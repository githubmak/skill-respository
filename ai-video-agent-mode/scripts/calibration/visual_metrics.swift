#!/usr/bin/env swift

import AVFoundation
import CoreGraphics
import Foundation

struct RasterFrame {
    let width: Int
    let height: Int
    let luminance: [Double]
    let red: [Double]
    let blue: [Double]
}

struct FrameStats {
    let luminanceMean: Double
    let highlightClipping: Double
    let shadowCrush: Double
    let redBlueBalance: Double
    let detailEnergy: Double
    let horizontalEdgePosition: Double
}

enum MetricError: Error, CustomStringConvertible {
    case message(String)

    var description: String {
        switch self {
        case .message(let text): return text
        }
    }
}

func mean(_ values: [Double]) -> Double {
    guard !values.isEmpty else { return 0 }
    return values.reduce(0, +) / Double(values.count)
}

func standardDeviation(_ values: [Double]) -> Double {
    guard values.count > 1 else { return 0 }
    let average = mean(values)
    return sqrt(mean(values.map { ($0 - average) * ($0 - average) }))
}

func rounded(_ value: Double) -> Double {
    return (value * 1_000_000).rounded() / 1_000_000
}

func frameStats(_ frame: RasterFrame) -> FrameStats {
    let count = frame.luminance.count
    guard count > 0 else {
        return FrameStats(
            luminanceMean: 0, highlightClipping: 0, shadowCrush: 0,
            redBlueBalance: 0, detailEnergy: 0, horizontalEdgePosition: 0
        )
    }
    let highlights = frame.luminance.filter { $0 >= 0.96 }.count
    let shadows = frame.luminance.filter { $0 <= 0.04 }.count
    let colorBalance = zip(frame.red, frame.blue).map { $0 - $1 }
    var detailSum = 0.0
    var detailCount = 0
    var rowEdges = [Double](repeating: 0, count: frame.height)
    if frame.width > 1 && frame.height > 1 {
        for y in 0..<frame.height {
            for x in 0..<frame.width {
                let index = y * frame.width + x
                if x > 0 {
                    detailSum += abs(frame.luminance[index] - frame.luminance[index - 1])
                    detailCount += 1
                }
                if y > 0 {
                    let edge = abs(frame.luminance[index] - frame.luminance[index - frame.width])
                    detailSum += edge
                    detailCount += 1
                    rowEdges[y] += edge
                }
            }
        }
    }
    let strongestRow = rowEdges.enumerated().max { $0.element < $1.element }?.offset ?? 0
    let edgePosition = frame.height > 1 ? Double(strongestRow) / Double(frame.height - 1) : 0
    return FrameStats(
        luminanceMean: mean(frame.luminance),
        highlightClipping: Double(highlights) / Double(count),
        shadowCrush: Double(shadows) / Double(count),
        redBlueBalance: mean(colorBalance),
        detailEnergy: detailCount > 0 ? detailSum / Double(detailCount) : 0,
        horizontalEdgePosition: edgePosition
    )
}

func rasterize(_ image: CGImage) throws -> RasterFrame {
    let width = image.width
    let height = image.height
    guard width > 0 && height > 0 else { throw MetricError.message("empty image") }
    var pixels = [UInt8](repeating: 0, count: width * height * 4)
    let rendered = pixels.withUnsafeMutableBytes { rawBuffer -> Bool in
        guard let context = CGContext(
            data: rawBuffer.baseAddress,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: CGColorSpaceCreateDeviceRGB(),
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return false }
        context.interpolationQuality = .medium
        context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
        return true
    }
    guard rendered else { throw MetricError.message("could not create bitmap context") }
    var luminance = [Double]()
    var red = [Double]()
    var blue = [Double]()
    luminance.reserveCapacity(width * height)
    red.reserveCapacity(width * height)
    blue.reserveCapacity(width * height)
    for offset in stride(from: 0, to: pixels.count, by: 4) {
        let r = Double(pixels[offset]) / 255.0
        let g = Double(pixels[offset + 1]) / 255.0
        let b = Double(pixels[offset + 2]) / 255.0
        red.append(r)
        blue.append(b)
        luminance.append(0.2126 * r + 0.7152 * g + 0.0722 * b)
    }
    return RasterFrame(width: width, height: height, luminance: luminance, red: red, blue: blue)
}

func frameDelta(_ first: RasterFrame, _ second: RasterFrame) -> Double? {
    guard first.width == second.width, first.height == second.height else { return nil }
    return mean(zip(first.luminance, second.luminance).map { abs($0 - $1) })
}

func analyzeVideo(path: String, samples: Int) throws -> [String: Any] {
    let absolutePath = URL(fileURLWithPath: path).standardizedFileURL.path
    guard FileManager.default.fileExists(atPath: absolutePath) else {
        throw MetricError.message("video does not exist: \(absolutePath)")
    }
    let asset = AVURLAsset(url: URL(fileURLWithPath: absolutePath))
    guard let track = asset.tracks(withMediaType: .video).first else {
        throw MetricError.message("no video track: \(absolutePath)")
    }
    let duration = CMTimeGetSeconds(asset.duration)
    guard duration.isFinite, duration > 0 else {
        throw MetricError.message("invalid video duration: \(absolutePath)")
    }
    let transformed = track.naturalSize.applying(track.preferredTransform)
    let sourceWidth = Int(abs(transformed.width).rounded())
    let sourceHeight = Int(abs(transformed.height).rounded())
    let generator = AVAssetImageGenerator(asset: asset)
    generator.appliesPreferredTrackTransform = true
    generator.maximumSize = CGSize(width: 96, height: 54)
    generator.requestedTimeToleranceBefore = .zero
    generator.requestedTimeToleranceAfter = .zero

    var frames = [RasterFrame]()
    for index in 0..<samples {
        let seconds = duration * (Double(index) + 0.5) / Double(samples)
        let time = CMTime(seconds: seconds, preferredTimescale: 600)
        do {
            let image = try generator.copyCGImage(at: time, actualTime: nil)
            frames.append(try rasterize(image))
        } catch {
            continue
        }
    }
    guard frames.count >= max(3, samples / 2) else {
        throw MetricError.message("too few decodable sample frames: \(frames.count)/\(samples)")
    }
    let stats = frames.map(frameStats)
    var deltas = [Double]()
    if frames.count > 1 {
        for index in 1..<frames.count {
            if let value = frameDelta(frames[index - 1], frames[index]) {
                deltas.append(value)
            }
        }
    }
    let luminance = stats.map { $0.luminanceMean }
    let highlights = stats.map { $0.highlightClipping }
    let shadows = stats.map { $0.shadowCrush }
    let colorBalance = stats.map { $0.redBlueBalance }
    let detail = stats.map { $0.detailEnergy }
    let horizontalEdge = stats.map { $0.horizontalEdgePosition }
    return [
        "path": absolutePath,
        "metrics": [
            "duration_seconds": rounded(duration),
            "source_width": sourceWidth,
            "source_height": sourceHeight,
            "sample_count": frames.count,
            "luminance_mean": rounded(mean(luminance)),
            "luminance_drift": rounded(standardDeviation(luminance)),
            "highlight_clipping_mean": rounded(mean(highlights)),
            "highlight_clipping_max": rounded(highlights.max() ?? 0),
            "shadow_crush_mean": rounded(mean(shadows)),
            "shadow_crush_max": rounded(shadows.max() ?? 0),
            "red_blue_balance_mean": rounded(mean(colorBalance)),
            "red_blue_balance_drift": rounded(standardDeviation(colorBalance)),
            "detail_energy_mean": rounded(mean(detail)),
            "detail_energy_flicker": rounded(standardDeviation(detail)),
            "frame_delta_mean": rounded(mean(deltas)),
            "frame_delta_std": rounded(standardDeviation(deltas)),
            "frame_delta_max": rounded(deltas.max() ?? 0),
            "horizontal_edge_proxy_position_drift": rounded(standardDeviation(horizontalEdge)),
        ],
    ]
}

func selfTest() -> [String: Any] {
    let width = 12
    let height = 8
    var first = [Double](repeating: 0.2, count: width * height)
    var second = first
    for y in 3..<height {
        for x in 0..<width {
            first[y * width + x] = 0.8
        }
    }
    for y in 4..<height {
        for x in 0..<width {
            second[y * width + x] = 1.0
        }
    }
    let frameA = RasterFrame(width: width, height: height, luminance: first, red: first, blue: first)
    let frameB = RasterFrame(width: width, height: height, luminance: second, red: second, blue: second)
    let statsA = frameStats(frameA)
    let statsB = frameStats(frameB)
    let delta = frameDelta(frameA, frameB) ?? 0
    let passed = statsB.highlightClipping > statsA.highlightClipping
        && statsA.horizontalEdgePosition != statsB.horizontalEdgePosition
        && delta > 0
    return [
        "pass": passed,
        "checks": [
            "highlight_increase": statsB.highlightClipping > statsA.highlightClipping,
            "edge_proxy_moves": statsA.horizontalEdgePosition != statsB.horizontalEdgePosition,
            "frame_delta_positive": delta > 0,
        ],
    ]
}

func emitJSON(_ payload: [String: Any]) {
    do {
        let data = try JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys])
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
    } catch {
        FileHandle.standardError.write(Data("JSON serialization failed: \(error)\n".utf8))
        exit(1)
    }
}

var arguments = Array(CommandLine.arguments.dropFirst())
if arguments == ["--self-test"] {
    let result = selfTest()
    emitJSON(result)
    exit(result["pass"] as? Bool == true ? 0 : 1)
}

var sampleCount = 18
if let index = arguments.firstIndex(of: "--samples") {
    guard index + 1 < arguments.count, let parsed = Int(arguments[index + 1]), (4...120).contains(parsed) else {
        emitJSON(["pass": false, "errors": ["--samples must be between 4 and 120"]])
        exit(1)
    }
    sampleCount = parsed
    arguments.removeSubrange(index...(index + 1))
}
guard !arguments.isEmpty else {
    emitJSON(["pass": false, "errors": ["provide at least one video path"]])
    exit(1)
}

var videos = [[String: Any]]()
var errors = [String]()
for path in arguments {
    do {
        videos.append(try analyzeVideo(path: path, samples: sampleCount))
    } catch {
        errors.append("\(path): \(error)")
    }
}
emitJSON(["pass": errors.isEmpty, "videos": videos, "errors": errors])
exit(errors.isEmpty ? 0 : 1)
