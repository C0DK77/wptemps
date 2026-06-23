# Distribuer wptemps (gratuit : GitHub + Homebrew)

> Cible : **macOS Apple Silicon**. L'app n'est pas signee par un compte
> developpeur Apple → au 1er lancement l'utilisateur fait **clic-droit → Ouvrir**.

## 1. Fabriquer le .dmg

```bash
bash scripts/make-dmg.sh 1.0.0
```

Produit `dist/wptemps-1.0.0.dmg` et affiche son **sha256** (à reporter dans le cask).

## 2. Publier sur GitHub

```bash
gh auth login                         # une fois (ton compte)
gh repo create wptemps --public --source=. --remote=origin --push
gh release create v1.0.0 dist/wptemps-1.0.0.dmg \
  --title "wptemps 1.0.0" \
  --notes "Overlay temperatures + infos materiel (Apple Silicon). 1er lancement : clic-droit -> Ouvrir."
```

(Sans `gh` : crée le dépôt sur github.com, `git remote add origin …`, `git push -u origin main`,
puis crée la Release et téléverse le `.dmg` à la main.)

## 3. Proposer l'installation par Homebrew (ton propre tap)

1. Crée un dépôt public **`homebrew-tap`** sur ton compte.
2. Mets-y `Casks/wptemps.rb` (copie celui de ce repo), en remplaçant
   `C0DK77` et le `sha256` par celui du `.dmg`.
3. Les utilisateurs installent ainsi :

```bash
brew tap C0DK77/tap
brew trust c0dk77/tap              # requis pour un tap tiers
brew install --cask wptemps          # ajouter --no-quarantine pour eviter le clic-droit
```

## 4. Communiquer aux utilisateurs

- **Télécharger** : page *Releases* du dépôt → `wptemps-x.y.z.dmg` → glisser l'app dans
  Applications → **clic-droit → Ouvrir** la 1ʳᵉ fois.
- **Ou** : `brew tap C0DK77/tap && brew install --cask wptemps`.
- L'app vit dans la **barre de menus** (icône 🌡) ; pas d'icône Dock, pas de fenêtre.

## Mises à jour

Incrémente la version (`scripts/make-dmg.sh 1.1.0`), crée une nouvelle Release, et mets à
jour `version` + `sha256` dans le cask de ton tap.

## Aller plus loin (optionnel, payant)

Un **Apple Developer ID** (99 $/an) permet de **signer + notariser** l'app : elle s'ouvre alors
d'un simple double-clic, sans avertissement, pour tout le monde. C'est la seule voie vraiment
grand public.
