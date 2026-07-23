import AppKit
import PDFKit

let arguments = CommandLine.arguments
guard arguments.count == 3 else {
    fputs("Usage: render_pdf.swift input.pdf output-directory\n", stderr)
    exit(1)
}

let inputURL = URL(fileURLWithPath: arguments[1])
let outputURL = URL(fileURLWithPath: arguments[2], isDirectory: true)

guard let document = PDFDocument(url: inputURL) else {
    fputs("Could not open PDF.\n", stderr)
    exit(1)
}

try FileManager.default.createDirectory(
    at: outputURL,
    withIntermediateDirectories: true
)

for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2
    let pixelSize = NSSize(
        width: bounds.width * scale,
        height: bounds.height * scale
    )
    let image = NSImage(size: pixelSize)

    image.lockFocus()
    NSColor.white.setFill()
    NSRect(origin: .zero, size: pixelSize).fill()

    guard let context = NSGraphicsContext.current?.cgContext else {
        image.unlockFocus()
        continue
    }
    context.saveGState()
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    context.restoreGState()
    image.unlockFocus()

    guard
        let tiff = image.tiffRepresentation,
        let bitmap = NSBitmapImageRep(data: tiff),
        let png = bitmap.representation(using: .png, properties: [:])
    else {
        continue
    }

    let pageURL = outputURL.appendingPathComponent(
        String(format: "page-%02d.png", index + 1)
    )
    try png.write(to: pageURL)
}

print("Rendered \(document.pageCount) pages.")
