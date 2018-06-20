
Originally the indices for labels were hard-coded knowledge within different
tools but this has since been generalized so tools can read these label-map
.json files instead.

For example when we run the `image-pre-processor` tool then we can use the
`2018-06-render-to-2018-06-rdt-map.json` to map from the indices Blender writes
out for labels to the packed indices of labels used while training and stored
in the decision trees.

The maps can also be used to aggregate high-level labels when measuring and
reporting accuracy metrics.

The scheme has changed a few times (primarily to ensure index zero corresponds
to the background label) and the dates help make it clear when a file describes
a mapping between old/new schemes.

* `rdt` refers to the labels of 'random decision trees'.
* `test` refers to the labels for 'test'/training data.
* `out` refers to the aggregate 'output' labels displayed when testing and
reporting the accuracy of decision trees.
