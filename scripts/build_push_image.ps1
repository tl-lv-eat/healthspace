# Build jianfei image (with git remote bound) and push to Aliyun ACR.
# Usage:
#   $env:GIT_REMOTE = "https://gitee.com/you/jianfei.git"   # or git@...
#   $env:ACR_IMAGE  = "registry.cn-hangzhou.aliyuncs.com/<ns>/jianfei:latest"
#   $env:ACR_USER   = "<acr-user>"
#   $env:ACR_PASS   = "<acr-password-or-token>"
#   .\scripts\build_push_image.ps1

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..")

if (-not $env:GIT_REMOTE) {
  $env:GIT_REMOTE = (git remote get-url origin 2>$null)
}
if (-not $env:GIT_REMOTE) {
  throw "Set GIT_REMOTE or add git remote 'origin' first."
}
if (-not $env:ACR_IMAGE) {
  throw "Set ACR_IMAGE, e.g. registry.cn-hangzhou.aliyuncs.com/my-ns/jianfei:latest"
}

$tag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "jianfei:latest" }

Write-Host "GIT_REMOTE=$env:GIT_REMOTE"
Write-Host "Building $tag ..."
docker build `
  --build-arg "GIT_REMOTE=$env:GIT_REMOTE" `
  -t $tag `
  -t $env:ACR_IMAGE `
  .

if ($env:ACR_USER -and $env:ACR_PASS) {
  $registry = ($env:ACR_IMAGE -split "/")[0]
  Write-Host "Login $registry ..."
  $env:ACR_PASS | docker login $registry -u $env:ACR_USER --password-stdin
}

Write-Host "Push $($env:ACR_IMAGE) ..."
docker push $env:ACR_IMAGE
Write-Host "Done."
