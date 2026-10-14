import AppKit
import Foundation
import PDFKit
import Vision

struct OCRPage: Codable {
    let page: Int
    let text: String
    let error: String?
}

struct OCRDocument: Codable {
    let source: String
    let engine: String
    let generatedAt: String
    let pages: [OCRPage]
}

func recognize(page: PDFPage, index: Int) -> OCRPage {
    autoreleasepool {
        let bounds = page.bounds(for: .mediaBox)
        let maximumWidth: CGFloat = 1800
        let scale = min(2.2, maximumWidth / max(bounds.width, 1))
        let size = NSSize(width: max(1, bounds.width * scale), height: max(1, bounds.height * scale))
        let image = page.thumbnail(of: size, for: .mediaBox)
        var proposed = NSRect(origin: .zero, size: image.size)
        guard let cgImage = image.cgImage(forProposedRect: &proposed, context: nil, hints: nil) else {
            return OCRPage(page: index + 1, text: "", error: "render_failed")
        }

        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        request.recognitionLanguages = ["en-US"]
        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        do {
            try handler.perform([request])
            let observations = request.results ?? []
            // USPTO documents use two text columns. Reading each complete column
            // before the next avoids interleaving claim language with description.
            let leftColumn = observations.filter { $0.boundingBox.midX < 0.5 }.sorted {
                if abs($0.boundingBox.maxY - $1.boundingBox.maxY) > 0.01 {
                    return $0.boundingBox.maxY > $1.boundingBox.maxY
                }
                return $0.boundingBox.minX < $1.boundingBox.minX
            }
            let rightColumn = observations.filter { $0.boundingBox.midX >= 0.5 }.sorted {
                if abs($0.boundingBox.maxY - $1.boundingBox.maxY) > 0.01 {
                    return $0.boundingBox.maxY > $1.boundingBox.maxY
                }
                return $0.boundingBox.minX < $1.boundingBox.minX
            }
            let ordered = leftColumn + rightColumn
            let lines = ordered.compactMap { $0.topCandidates(1).first?.string }
            return OCRPage(page: index + 1, text: lines.joined(separator: "\n"), error: nil)
        } catch {
            return OCRPage(page: index + 1, text: "", error: String(describing: error))
        }
    }
}

let arguments = CommandLine.arguments
if arguments.count == 3 && arguments[1] == "--page-count" {
    guard let countDocument = PDFDocument(url: URL(fileURLWithPath: arguments[2])) else {
        FileHandle.standardError.write(Data("could not open PDF\n".utf8))
        exit(3)
    }
    print(countDocument.pageCount)
    exit(0)
}
if arguments.count != 3 && arguments.count != 5 {
    FileHandle.standardError.write(Data("usage: vision-ocr INPUT.pdf OUTPUT.json [START_PAGE END_PAGE]\n".utf8))
    exit(2)
}

let input = arguments[1]
let output = arguments[2]
guard let document = PDFDocument(url: URL(fileURLWithPath: input)) else {
    FileHandle.standardError.write(Data("could not open PDF\n".utf8))
    exit(3)
}

let requestedStart = arguments.count == 5 ? (Int(arguments[3]) ?? 1) : 1
let requestedEnd = arguments.count == 5 ? (Int(arguments[4]) ?? document.pageCount) : document.pageCount
let startIndex = max(0, min(document.pageCount, requestedStart - 1))
let endIndex = max(startIndex, min(document.pageCount, requestedEnd))

var pages: [OCRPage] = []
for index in startIndex..<endIndex {
    guard let page = document.page(at: index) else {
        pages.append(OCRPage(page: index + 1, text: "", error: "page_unavailable"))
        continue
    }
    pages.append(recognize(page: page, index: index))
}

let formatter = ISO8601DateFormatter()
formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
let result = OCRDocument(
    source: URL(fileURLWithPath: input).lastPathComponent,
    engine: "Apple Vision VNRecognizeTextRequest accurate",
    generatedAt: formatter.string(from: Date()),
    pages: pages
)
let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
do {
    let data = try encoder.encode(result)
    try data.write(to: URL(fileURLWithPath: output), options: .atomic)
} catch {
    FileHandle.standardError.write(Data("could not write output: \(error)\n".utf8))
    exit(4)
}
