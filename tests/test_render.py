from PIL import Image

from wptemps.config import Config
from wptemps.metrics.base import Metrics
from wptemps.render import render


def _base():
    return Image.new("RGB", (400, 300), (0, 0, 0))  # fond noir uni


def test_render_preserves_size_and_mode():
    out = render(Metrics(cpu_temp=55.0), _base(), Config())
    assert out.size == (400, 300)
    assert out.mode == "RGB"


def test_render_draws_text_pixels():
    base = _base()
    out = render(Metrics(cpu_temp=55.0, gpu_temp=48.0), base, Config())
    # au moins un pixel non-noir => du texte a ete dessine
    assert any(px != (0, 0, 0) for px in out.getdata())


def test_render_does_not_mutate_base():
    base = _base()
    before = list(base.getdata())
    render(Metrics(cpu_temp=55.0), base, Config())
    assert list(base.getdata()) == before  # base inchangee
