# Quake demo Ring of Shadows fixer

When the player picks up the Ring of Shadows (invisibility) in Quake, they
appear as just a pair of eyes in the third-person view.  This is awkward for
recams and ghosts since the player becomes very hard to see.

This script modifies Quake demos so that the player appears as normal when the
RoS is active.

## Usage

Clone [kugelrund's pydem repo](https://github.com/kugelrund/pydem) and this
repo:

```bash
git clone git@github.com:kugelrund/pydem.git
git clone git@github.com:matthewearl/showros.git
```

Run the following to convert a demo:

```bash
PYTHONPATH=pydem python showros/showros.py e4m2_116.dem e4m2_116_fixed.dem
```

## Limitations

I made this very quickly and it probably has bugs / could be made more accurate.
One limitation is that the player never has a standing animation, since I
couldn't find a good heuristic in the demo data.  Feel free to fork and improve.
