These configs can be passed to the `image-pre-processor` tool via the
`-c,--config` option and follow this schema:

```javascript
{
    "properties": {
        "no_flip": false,               // Don't create flipped frames
        "background_depth_m": 32.0,     // The depth of background pixels
        "no_bg_depth_clamp": false,     // Don't clamp background depth to background_depth_m
        "min_body_size_px": 3000,       // discard frame if body has fewer pixels
        "min_body_change_percent": 0.1, // discard frame if changed less than
                                        // this relative to previous frame
    },
    "noise": [
        {
            "foreground-edge-swizzle"
        },
        {
            "type": "gaussian",
            "fwtm_range_map_m": 0.02
        },
        {
            "type": "perlin",
            "freq": 0.1,
            "amplitude_m": 0.15,
            "octaves": 4
        }
    ]
}
```

## Noise

The noise configuration helps us model different types of sensor noise so that
our training data is a more realistic representation of the data we will see
from real cameras.

### Foreground Edge Swizzle

This simply adds noise to the silhouette of our cleanly rendered bodies. This
is done with a 3x3 sliding window and when the center pixel is an edge between
the background and the body then one of its 8 neighbours is randomly picked to
replace the edge pixel.

### Gaussian

In the case of "gaussian" noise then the amplitude is controlled by mapping
the FWTM range (Full Width at Tenth of Maximum) to a range in meters. The most
likely samples at the mean, center, of the gaussian distribution will correspond
to zero depth offset. The less likely samples at the point where the gaussian
curve is 1/10th of the maximum will correspond to +/- *half* the `fwtm_range_map_m`
property value, in meters. 

_Note: since curve has a mean of zero, the FWTM range goes from negative to
positive and a `"fwtm_range_map_m"` of `0.02` (2cm) would roughly equate to a
applying +/- (up to) 1cm offsets to the depth values._

## Perlin

In the case of "perlin" noise then "freq" is a frequency in pixels (so notably
may need changing if the resolution of training images is changed), "amplitude_m"
is the maximum amplitude in meters (range of offsets will be from
[-amplitude_m:amplitude_m]). If "octaves" is specified (default = 1), then
after applying the described perlin noise the frequency and amplitude will
be iteratively halved and applied N times.
