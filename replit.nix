{pkgs}: {
  deps = [
    pkgs.xsimd
    pkgs.libxcrypt
    pkgs.jack2
    pkgs.pulseaudio
    pkgs.alsa-utils
    pkgs.alsa-lib
    pkgs.portmidi
    pkgs.pkg-config
    pkgs.libpng
    pkgs.libjpeg
    pkgs.freetype
    pkgs.fontconfig
    pkgs.SDL2_ttf
    pkgs.SDL2_mixer
    pkgs.SDL2_image
    pkgs.SDL2
    pkgs.portaudio
  ];
}
