# Formule Homebrew Cask pour wptemps.
# A heberger dans TON tap (depot "homebrew-tap"). Remplace C0DK77
# et le sha256 (donne par scripts/make-dmg.sh) apres avoir cree la Release.
cask "wptemps" do
  version "1.1.0"
  sha256 "57a74c58d8a5229f0a218834d79d3fd5f8f87af918b2777bdc0e50aae6ed2a8f"

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
