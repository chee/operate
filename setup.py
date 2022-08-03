import setuptools

with open("readme.org", "r") as fh:
        long_description = fh.read()

setuptools.setup(
        name="operate-chee",
        version="0.0.0",
        author="chee",
        author_email="yay@chee.party",
        description="save them",
        long_description=long_description,
        long_description_content_type="text/org",
        url="https://github.com/chee/operate",
        packages=setuptools.find_packages(),
        python_requires=">= 3.6",
        entry_points={
                'console_scripts': [
                        "operate = operate.__main__:main"
                ]
        }
)
