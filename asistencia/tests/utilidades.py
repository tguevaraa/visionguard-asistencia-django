import numpy as np


def rostro_sintetico(semilla: int, ruido: int = 0, tamano: int = 200) -> np.ndarray:
    """Imagen en gris con una textura propia de cada 'persona' (semilla) + ruido opcional."""
    base = np.random.default_rng(semilla).integers(0, 256, (tamano // 10, tamano // 10), dtype=np.uint8)
    img = np.kron(base, np.ones((10, 10), dtype=np.uint8))
    if ruido:
        r = np.random.default_rng(semilla * 1000 + ruido).integers(-12, 13, img.shape)
        img = np.clip(img.astype(int) + r, 0, 255).astype(np.uint8)
    return img
