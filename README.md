# python-voronoi
### Introduction
This project is designed to produce Voronoi diagrams and Delaunay
triangulation in n-dimensions. We plan to allow the user to click and 
interact with a graphical representation (at least in 2 dimensions) to add 
points and see the effect that this has on the triangulation.

### Testing
To run all the tests, run `python -m unittest discover -v`.
To run a particular test, run `python -m unittest -v pyVor.tests.testPredicates`
(optionally replacing `testPredicates` with the test you actually want to run).

### Running Arbitrary Files
`python -m pyVor.path.to.file`
