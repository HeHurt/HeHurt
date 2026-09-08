from pathlib import Path


path = Path(r"D:\Users\hez\Desktop\hithium\params\paramsLDSCW501.py")
text = path.read_text(encoding="utf-8")

replacements = {
    '"Negative electrode thickness [m]": 11.3e-05,': '"Negative electrode thickness [m]": 113.525e-6,',
    '"Positive electrode thickness [m]": 13.67e-05,': '"Positive electrode thickness [m]": 135.7125e-6,',
    '"Negative particle radius [m]": 4.5e-6,': '"Negative particle radius [m]": 5.5e-6,',
    '"Positive particle radius [m]": 5.5e-7,': '"Positive particle radius [m]": 0.45e-6,',
    '"Electrode height [m]": 0.557,': '"Electrode height [m]": 0.555,',
    '"Electrode width [m]": 213.5*61*2*2,': '"Electrode width [m]": 0.2135 * 61 * 2 * 2,',
    '"Nominal cell capacity [A.h]": 1300,': '"Nominal cell capacity [A.h]": 1361.9,',
}

for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one occurrence of {old!r}, found {count}")
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
print(f"Updated {path}")
