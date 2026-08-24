#!/usr/bin/env python3
"""Encrypt a folder of deck slide JPEGs into a single pack for the Directive 17 site.

Usage:
    python3 tools/encrypt_deck.py <slides_dir> <slug> "<Company Name>" <password>

Reads slide images (sorted), encrypts each with AES-256-GCM (key from PBKDF2-SHA256,
300k iterations), concatenates the encrypted slides into ONE file, and writes:
    content/decks/<slug>.pack   (concat of per-slide [12-byte iv | ciphertext+tag])
    content/decks/<slug>.json   (salt, iterations, title, per-slide byte sizes)

Only ciphertext is committed. The password is never stored anywhere.
build.py copies content/decks/ into docs/decks/ and generates the viewer page,
which fetches slides lazily via HTTP Range requests.
"""
import sys, os, json, base64, glob
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITER = 300_000

def main():
    slides_dir, slug, title, password = sys.argv[1:5]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "content", "decks")
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(slides_dir, "*.jpg")) +
                   glob.glob(os.path.join(slides_dir, "*.jpeg")) +
                   glob.glob(os.path.join(slides_dir, "*.png")))
    if not files:
        sys.exit("no slide images found")
    salt = os.urandom(16)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt,
                     iterations=ITER).derive(password.encode())
    aes = AESGCM(key)
    sizes = []
    with open(os.path.join(out_dir, f"{slug}.pack"), "wb") as pack:
        for f in files:
            iv = os.urandom(12)
            blob = iv + aes.encrypt(iv, open(f, "rb").read(), None)
            pack.write(blob)
            sizes.append(len(blob))
    json.dump({"salt": base64.b64encode(salt).decode(), "iterations": ITER,
               "title": title, "sizes": sizes},
              open(os.path.join(out_dir, f"{slug}.json"), "w"))
    print(f"{slug}: {len(files)} slides -> content/decks/{slug}.pack "
          f"({sum(sizes)//1024} KB)")

if __name__ == "__main__":
    main()
