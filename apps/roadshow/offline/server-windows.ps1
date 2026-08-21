$ErrorActionPreference = "Stop"
$root = Join-Path $PSScriptRoot "site"
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:13110/")
$listener.Start()
while ($listener.IsListening) {
  $context = $listener.GetContext()
  $relative = $context.Request.Url.LocalPath.TrimStart('/').Replace('/', [IO.Path]::DirectorySeparatorChar)
  $file = Join-Path $root $(if ($relative) { $relative } else { "index.html" })
  if (!(Test-Path $file -PathType Leaf)) { $file = Join-Path $root "index.html" }
  $bytes = [IO.File]::ReadAllBytes($file)
  $types = @{ ".html"="text/html; charset=utf-8"; ".js"="text/javascript; charset=utf-8"; ".css"="text/css; charset=utf-8"; ".json"="application/json; charset=utf-8"; ".geojson"="application/geo+json; charset=utf-8"; ".png"="image/png"; ".jpg"="image/jpeg"; ".jpeg"="image/jpeg"; ".webp"="image/webp"; ".svg"="image/svg+xml" }
  $extension = [IO.Path]::GetExtension($file).ToLowerInvariant()
  $context.Response.ContentType = $(if ($types[$extension]) { $types[$extension] } else { "application/octet-stream" })
  $context.Response.ContentLength64 = $bytes.Length
  $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
  $context.Response.Close()
}
