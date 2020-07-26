import setuptools
with open("README.md", "r") as f:
	long_description = f.read()
setuptools.setup(
	name="dis2py",
	version="0.1",
	descripton="Converts dis.dis output into Python source code.",
	long_description=long_description,
	long_description_content_type="text/markdown",
	packages=["dis2py"],
	license="MIT",
	author="SuperStormer",
	author_email="larry.p.xue@gmail.com",
	url="https://github.com/SuperStormer/dis2py",
	project_urls={"Source Code": "https://github.com/SuperStormer/dis2py"},
	entry_points={"console_scripts": ["dis2py=dis2py.__main__:main"]}
)