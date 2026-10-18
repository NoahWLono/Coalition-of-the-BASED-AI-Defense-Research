# Third-party notices

CEDAR's original source code, documentation and generated synthetic corpus are covered by the repository's [MIT license](../LICENSE), copyright 2026 CEDAR contributors. The fictional suppliers, aircraft configurations, reports, quotations and advisories were created for this demonstration. They are not claims about real products or organizations.

## Vendored CycloneDX schemas

The repository includes these unmodified files from the [CycloneDX specification 1.6 source](https://github.com/CycloneDX/specification/tree/1.6/schema):

- `vendor/bom-1.6.schema.json`
- `vendor/jsf-0.82.schema.json`
- `vendor/spdx.schema.json`

CycloneDX is an OWASP Foundation project. Its [1.6 license](https://github.com/CycloneDX/specification/blob/1.6/LICENSE) states Apache License 2.0 and attributes copyright to the OWASP Foundation. The complete upstream license is retained as [vendor/LICENSE-CycloneDX](../vendor/LICENSE-CycloneDX). The BOM schema explicitly states Apache 2.0. The JSF schema also states Apache 2.0 and credits Anders Rundgren and the OpenKeyStore project for JSON Signature Format. The SPDX identifier enumeration is the copy supplied in the same CycloneDX 1.6 source tree.

All four local files were compared byte for byte with their upstream `1.6` paths during release preparation. Their recorded SHA-256 hashes are:

| Vendored file | SHA-256 |
| --- | --- |
| `LICENSE-CycloneDX` | `6c29f22a4a7385285c6f579ec9f33c5e989f00739d6b257243a0b082ec9447ae` |
| `bom-1.6.schema.json` | `3e92dddbc30cf7f6a02b80f0942b1a4cfd4fb1c26f1dfc4310afa9d613cafb93` |
| `jsf-0.82.schema.json` | `8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae` |
| `spdx.schema.json` | `baa9d3bd1ed57b6751b0887edead6b5063ff53ff7429cf85d476c6c94af0166e` |

The schemas support offline validation of the synthetic CycloneDX inventories. Including the JSF schema does not mean CEDAR creates or verifies digital signatures. The project and its output do not claim endorsement by OWASP, CycloneDX, OpenKeyStore or SPDX.

## Pinned Python dependencies

Direct requirements are pinned in [pyproject.toml](../pyproject.toml). The complete resolved environment, including transitive dependencies and distribution hashes, is recorded in [uv.lock](../uv.lock). The table below was read from the installed `.venv` distribution metadata during release preparation on 2026-10-17. It records the Linux validation environment; conditional dependencies on another platform may differ.

The license column uses `License-Expression` where supplied, then the distribution's `License` field. The final column lists its declared `License-File` entries. ReportLab's metadata uses a descriptive BSD label; its installed license text was separately inspected and contains the source, binary and endorsement conditions. No SPDX identifier has been substituted for that metadata label.

| Distribution | Installed version | Use | Reported license | Declared license files |
| --- | --- | --- | --- | --- |
| annotated-doc | `0.0.5` | Runtime transitive | MIT | `LICENSE` |
| annotated-types | `0.8.0` | Runtime transitive | MIT | `LICENSE` |
| anyio | `4.15.1` | Runtime transitive | MIT | `LICENSE` |
| attrs | `26.1.0` | Runtime transitive | MIT | `LICENSE` |
| charset-normalizer | `3.5.2` | Development transitive | MIT | `LICENSE` |
| click | `8.5.0` | Runtime transitive | BSD-3-Clause | `LICENSE.txt` |
| fastapi | `0.143.3` | Runtime direct | MIT | `LICENSE` |
| greenlet | `3.5.6` | Development transitive | MIT AND PSF-2.0 | `LICENSE`, `LICENSE.PSF` |
| h11 | `0.16.0` | Runtime transitive | MIT | `LICENSE.txt` |
| httpcore2 | `2.13.1` | Development transitive | BSD-3-Clause | `LICENSE.md` |
| httpx2 | `2.13.1` | Development direct | BSD-3-Clause | `LICENSE.md` |
| idna | `3.20` | Runtime transitive | BSD-3-Clause | `LICENSE.md` |
| iniconfig | `2.3.1` | Development transitive | MIT | `LICENSE` |
| jsonschema | `4.26.0` | Runtime direct | MIT | `COPYING` |
| jsonschema-specifications | `2025.9.1` | Runtime transitive | MIT | `COPYING` |
| Markdown | `3.11.1` | Development direct | BSD-3-Clause | `LICENSE.md` |
| opentelemetry-api | `1.45.1` | Runtime transitive | Apache-2.0 | `LICENSE` |
| packaging | `26.3` | Development transitive | Apache-2.0 OR BSD-2-Clause | `LICENSE`, `LICENSE.APACHE`, `LICENSE.BSD` |
| pillow | `13.0.0` | Development transitive | MIT-CMU | `LICENSE` |
| playwright | `1.64.0` | Development direct | Apache-2.0 | `LICENSE` |
| pluggy | `1.7.0` | Development transitive | MIT | `LICENSE` |
| pydantic | `2.14.1` | Runtime transitive | MIT | `LICENSE` |
| pydantic_core | `2.50.1` | Runtime transitive | MIT | `LICENSE` |
| pyee | `14.0.0` | Development transitive | MIT | `LICENSE` |
| Pygments | `2.21.0` | Development transitive | BSD-2-Clause | `AUTHORS`, `LICENSE` |
| pytest | `9.1.1` | Development direct | MIT | `LICENSE` |
| referencing | `0.37.0` | Runtime transitive | MIT | `COPYING` |
| reportlab | `5.0.1` | Development direct | BSD license (see license.txt for details), Copyright (c) 2000-2025, ReportLab Inc. | `LICENSE` |
| rpds-py | `2026.9.1` | Runtime transitive | MIT | `LICENSE` |
| starlette | `1.8.0` | Runtime transitive | BSD-3-Clause | `LICENSE.md` |
| truststore | `0.10.5` | Development transitive | MIT | `LICENSE` |
| typing_extensions | `4.16.0` | Runtime transitive | PSF-2.0 | `LICENSE` |
| typing-inspection | `0.4.4` | Runtime transitive | MIT | `LICENSE` |
| uvicorn | `0.54.0` | Runtime direct | BSD-3-Clause | `LICENSE.md` |

The source release excludes `.venv` and dependency wheels. These dependencies are installed through the lockfile when setting up the project. Their distribution license files remain available in the installed environment. The table reports package-level metadata; it does not replace notices for components bundled in a dependency's wheel. For example, Pillow's installed license file contains additional codec notices, and Playwright's browser installation has its own third-party notices.

Python, `uv`, browser executables and their caches are external tools and are not included in the source release. The screenshots and screen recording show CEDAR's own interface and synthetic corpus. Generated report artifacts retain the demonstration's limitations.

To inspect an installed distribution's metadata after setup:

```python
from importlib.metadata import distribution

d = distribution("fastapi")
print(d.metadata["Name"], d.version)
print(d.metadata.get("License-Expression") or d.metadata.get("License"))
print(d.metadata.get_all("License-File"))
```

When changing dependencies or vendored files, regenerate the lockfile as appropriate, inspect the new distributions' license metadata and notices, and update this inventory before rebuilding the source release.

## Bitstream Vera fonts in generated PDFs

The PDF builder uses `Vera.ttf`, `VeraBd.ttf`, `VeraIt.ttf` and `VeraBI.ttf` from the installed ReportLab `fonts` directory. PDF output can embed subsets of these typefaces. The fonts have their own Bitstream Vera license, separate from ReportLab's package license. The source TTF files are not copied from `.venv` into the source release.

The installed `reportlab/fonts/bitstream-vera-license.txt` was inspected during release preparation. Its copyright, trademark and permission notice is retained below for the generated PDFs. The source font file hashes used in that environment are:

| Font | SHA-256 |
| --- | --- |
| `Vera.ttf` | `c4c45690b345435b2cba52ecabe275f05e49b389b39fe68ad03afbb551288d3d` |
| `VeraBd.ttf` | `cc037385e4d55bfde89b13e03091ee93bf40c0c52ddd391ff031ab276f13b8e9` |
| `VeraIt.ttf` | `2adc684d518f45232c4ad1f56522f5a82a6904c31940373e1b7030beee20fb3a` |
| `VeraBI.ttf` | `fca0d4eeac1ced7e75e1b2274c869a351d2d83b5ed1f61d249e7bcc477c33ebe` |

```text
Copyright (c) 2003 by Bitstream, Inc. All Rights Reserved. Bitstream
Vera is a trademark of Bitstream, Inc.

Permission is hereby granted, free of charge, to any person obtaining
a copy of the fonts accompanying this license ("Fonts") and associated
documentation files (the "Font Software"), to reproduce and distribute
the Font Software, including without limitation the rights to use,
copy, merge, publish, distribute, and/or sell copies of the Font
Software, and to permit persons to whom the Font Software is furnished
to do so, subject to the following conditions:

The above copyright and trademark notices and this permission notice
shall be included in all copies of one or more of the Font Software
typefaces.

The Font Software may be modified, altered, or added to, and in
particular the designs of glyphs or characters in the Fonts may be
modified and additional glyphs or characters may be added to the
Fonts, only if the fonts are renamed to names not containing either
the words "Bitstream" or the word "Vera".

This License becomes null and void to the extent applicable to Fonts
or Font Software that has been modified and is distributed under the
"Bitstream Vera" names.

The Font Software may be sold as part of a larger software package but
no copy of one or more of the Font Software typefaces may be sold by
itself.

THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL
BITSTREAM OR THE GNOME FOUNDATION BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL,
OR CONSEQUENTIAL DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF THE USE OR INABILITY TO USE THE FONT
SOFTWARE OR FROM OTHER DEALINGS IN THE FONT SOFTWARE.

Except as contained in this notice, the names of Gnome, the Gnome
Foundation, and Bitstream Inc., shall not be used in advertising or
otherwise to promote the sale, use or other dealings in this Font
Software without prior written authorization from the Gnome Foundation
or Bitstream Inc., respectively. For further information, contact:
fonts at gnome dot org.
```
