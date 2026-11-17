"""Use the official pure-Python FontTools build for portable PDF rendering."""
import importlib.metadata
import subprocess
import sys

WHEEL='https://files.pythonhosted.org/packages/3d/61/4161946319472aaa9b897bd18ad5108a5b10f5ebaa503d921a001ac4fff9/fonttools-4.67.0-py3-none-any.whl#sha256=4304f03ed7f4ba000a8dcc941ad854bfa52e2f3b6112b8f099b6f431cf98e701'


def main():
    files=importlib.metadata.files('fonttools')
    native=any(str(p).endswith(('.pyd','.so')) for p in files)
    if importlib.metadata.version('fonttools')!='4.67.0' or native:
        subprocess.run([sys.executable,'-m','pip','install','--force-reinstall','--no-deps',WHEEL],check=True)
    subprocess.run([sys.executable,'-c','from fontTools import subset; import fontTools; print("FontTools PDF support",fontTools.version,"pure Python")'],check=True)


if __name__=='__main__':
    main()
