import setuptools
with open("README.md", "r") as f:
	long_description = f.read()
setuptools.setup(
	name="pyasm",
	version="0.1",
	descripton="assembles dis.dis output into python source code",
	long_description=long_description,
	long_description_content_type="text/markdown",
	packages=setuptools.find_packages(),
	license="MIT",
	author="SuperStormer",
	author_email="larry.p.xue@gmail.com",
	url="https://github.com/SuperStormer/pyasm",
	project_urls={"Source Code": "https://github.com/SuperStormer/pyasm"}
)