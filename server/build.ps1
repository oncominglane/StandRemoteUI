# Path to vcpkg toolchain
$toolchain = "C:/gvn/GUI_Marathon/vcpkg/scripts/buildsystems/vcpkg.cmake"

#1. CMake Project Generation
Write-Host ">>> Running CMake generation..."
cmake -B build -DCMAKE_TOOLCHAIN_FILE=$toolchain -DCMAKE_BUILD_TYPE=Release

#2. Question to the user
$response = Read-Host "Generation is complete. Should I continue building? (Y/N)"

if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ">>> I am building the project..."
    cmake --build build --config Release
    Write-Host ">>> Build completed!"
} else {
    Write-Host "The build was canceled by the user."
}
