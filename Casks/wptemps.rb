# Formule Homebrew Cask pour wptemps.
# A heberger dans TON tap (depot "homebrew-tap"). Remplace C0DK77
# et le sha256 (donne par scripts/make-dmg.sh) apres avoir cree la Release.
cask "wptemps" do
  version "1.0.0"
  sha256 "4bb49bef7406dfdbebc20eeaa0795378656233f895c8e7682c80edca7af6807b"

  url "https://github.com/C0DK77/wptemps/releases/download/v#{version}/wptemps-#{version}.dmg"
  name "wptemps"
  desc "Overlay des temperatures et infos materiel sur le bureau (Apple Silicon)"
  homepage "https://github.com/C0DK77/wptemps"

  depends_on arch: :arm64

  app "wptemps.app"

  caveats <<~EOS
    L'app n'est pas signee par un compte developpeur Apple. Au 1er lancement :
    clic-droit sur wptemps.app -> Ouvrir (ou installe avec --no-quarantine).
    Necessite `macmon` deja embarque ; Apple Silicon uniquement.
  EOS

  zap trash: [
    "~/Library/Application Support/wptemps",
  ]
end
