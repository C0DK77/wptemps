# Formule Homebrew Cask pour wptemps.
# A heberger dans TON tap (depot "homebrew-tap"). Remplace <TON_USER_GITHUB>
# et le sha256 (donne par scripts/make-dmg.sh) apres avoir cree la Release.
cask "wptemps" do
  version "1.0.0"
  sha256 "11151c304f6e2604d243997b654a3dec438f1eee0697a1601a08cafa8a6bb33d"

  url "https://github.com/<TON_USER_GITHUB>/wptemps/releases/download/v#{version}/wptemps-#{version}.dmg"
  name "wptemps"
  desc "Overlay des temperatures et infos materiel sur le bureau (Apple Silicon)"
  homepage "https://github.com/<TON_USER_GITHUB>/wptemps"

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
