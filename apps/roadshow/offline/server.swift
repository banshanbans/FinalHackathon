import Foundation
import Network

let port: UInt16 = 13110
let siteRoot = URL(fileURLWithPath: FileManager.default.currentDirectoryPath).appendingPathComponent("site")
let listener = try NWListener(using: .tcp, on: NWEndpoint.Port(rawValue: port)!)
let queue = DispatchQueue(label: "cn.13110.offline-server")
let mime: [String: String] = [
  "html": "text/html; charset=utf-8", "js": "text/javascript; charset=utf-8",
  "css": "text/css; charset=utf-8", "json": "application/json; charset=utf-8", "geojson": "application/geo+json; charset=utf-8",
  "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
  "svg": "image/svg+xml", "ico": "image/x-icon"
]

func serve(_ connection: NWConnection) {
  connection.start(queue: queue)
  connection.receive(minimumIncompleteLength: 1, maximumLength: 8192) { data, _, _, _ in
    guard let data, let request = String(data: data, encoding: .utf8) else { connection.cancel(); return }
    let rawPath = request.split(separator: " ").dropFirst().first.map(String.init) ?? "/"
    let decoded = rawPath.removingPercentEncoding ?? "/"
    let safe = decoded.split(separator: "/").filter { $0 != ".." }.joined(separator: "/")
    var file = siteRoot.appendingPathComponent(safe.isEmpty ? "index.html" : safe)
    var isDirectory: ObjCBool = false
    if !FileManager.default.fileExists(atPath: file.path, isDirectory: &isDirectory) || isDirectory.boolValue {
      file = siteRoot.appendingPathComponent("index.html")
    }
    let body = (try? Data(contentsOf: file)) ?? Data()
    let type = mime[file.pathExtension.lowercased()] ?? "application/octet-stream"
    let header = "HTTP/1.1 200 OK\r\nContent-Type: \(type)\r\nContent-Length: \(body.count)\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"
    var response = Data(header.utf8); response.append(body)
    connection.send(content: response, completion: .contentProcessed { _ in connection.cancel() })
  }
}

listener.newConnectionHandler = serve
listener.stateUpdateHandler = { state in
  if case .ready = state { print("13110 offline server ready: http://127.0.0.1:\(port)/") }
}
listener.start(queue: queue)
dispatchMain()
