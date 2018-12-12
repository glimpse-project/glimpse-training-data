
This is an overview of the schema used to configure rendering:
_(Note: only one mode of "camera" would be included in a real config)_

```
{
    "filters": {
        "tag_whitelist": "all",
        "tag_blacklist": ["backflip"],
        "tag_skip_percentages": {
            "example": 20
        },
        "body_whitelist": ["Man0", "Woman0"],
        "clothes_whitelist": ["m_trousers_01"],
        "skip_percentage": 90,
    },
    "clothing_step": 5,
    "add_background": False,
    "camera": {
        "type": "iPhone X Training",
        "width": 320,
        "height": 240,
        "vertical_fov": 43.940769,
        "position": {
            "mode": "randomized",
            "min_distance": 2,
            "max_distance": 2.5,
            "min_height": 1.1,
            "max_height": 1.4,
            "focus_bone": "pelvis",
            "min_horizontal_rotation": -30,
            "max_horizontal_rotation": 0
        }
    },
    "camera": {
        "type": "iPhone X Test Fixed",
        "width": 640,
        "height": 480,
        "vertical_fov": 43.940769,
        "position": {
            "mode": "fixed",
            "distance": 2,
            "height": 1.1,
            "focus_bone": "pelvis",
            "horizontal_rotation": 0
        }
    },
    "camera": {
        "type": "iPhone X Test Handheld",
        "width": 640,
        "height": 480,
        "vertical_fov": 43.940769,
        "position": {
            "mode": "smooth",
            "drift_frequency": 1,
            "min_distance": 2,
            "max_distance": 2.5,
            "min_height": 1.1,
            "max_height": 1.4,
            "focus_bone": "pelvis",
            "min_horizontal_rotation": -30,
            "max_horizontal_rotation": 0
        }
    },
    "camera": {
        "type": "iPhone X Test Debug",
        "width": 640,
        "height": 480,
        "vertical_fov": 43.940769,
        "position": {
            "mode": "debug",
        }
    }
}
```


Note: `horizontal_rotation`, `min_horizontal_rotation`
and `max_horizontal_rotation` accept values within the range [-180, 180].
