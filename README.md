# Construction Task Activities Taxonomy

This directory contains the action primitives, skills and video annotations for TARCAT (Taxonomy of Construction Task Activities for Robot Workers). The taxonomy is derived based on instructional Youtube videos of construction tasks across different occupations.  

`primitives.json` contains the taxonomy of primitive actions. `composite/` directory contains composite actions, also termed as skills.

## Labeling Videos

TARCAT taxonomy aims to identify the distinct activities that are performed during construction tasks and label those activies under a taxonomy. The human viewer watched the full video and determined the distinct significant activities required in order to perform the task. This identification eliminates the need for comprehensively annotation of the full video. So, only labels for the distinct activities observed during the video are provided. If the same activity is repeated in a contiguous segment, then the whole segment is labeled with the activity and the `repeated` property of the activity is set to `true`. If the same activity is performed in different context in that same video, both activities are also labeled separately. However, repetation of the same activity in the same context in that video is not labeled.

The TARCAT taxonomy also aims to understand all key activities to perform a construction task. Sometimes the speaker mentions a required activity or an activity is evident as a prerequisite for a sub-task, but it may not be demonstrated in the video. Such activities are included in the activities list for the sake of completeness and the `segment` for such activity is set to an empty string (`""`).

## Format

### Primitive Actions

There are 3 broad `classes` of the primitive acions. Each has this format in the `primitives.json` file

```json
{
  "key": {
    "name": "NAME",
    "description": "DESCRIPTION",
    "groups": [
      {
        "name": "GROUP_NAME",
        "description": "GROUP_DESCRIPTION",
        "primitives": ["PRIMITIVE_NAME"]
      }
    ],
    "primitives": [
      {
        "name": "PRIMITIVE_NAME",
        "description": "PRIMITIVE_DESCRIPTION",
        "examples": ["EXAMPLE"]
      }
    ]
  } 
}
```


### Skills

The composite actions or `skills` are organized into `skill families` such as `cutting` and `piercing`. Each skill family is a separate file in `composite/` directory. Each skill family file has the following format  

```json
{
  "skills": [
    {
      "name": "Composite - NAME",
      "description": "DESCRIPTION",
      "variables": ["VARIABLE"],
      "steps": [
        {
          "activity": "ACTIVITY",
          "category": "PRIMITIVE_OR_SKILL_NAME",
          "repeated": "BOOLEAN_TYPE"
        }
      ],
      "examples": ["EXAMPLE"]
    }
  ] 
}
```

The `variables` list contains placeholder names for items that are used or acted on when executing this skill. These placeholder names are used when describing the `steps`. In the video labeling, when an activity is marked as a skill, it also provides a mapping from the variable names to the specific items for that activity. As an example, `"tool"` might be a variable in a skill and `"hammer"` can be the specific item for that variable in an activity. 

The `steps` property lists the activity steps for a skill. The activities are listed in the order they are initiated the first time. After initiation, multiple activities may need to be performed together or repeated in the provided order a few times to successfully complete the skill. For example, when drilling a hole, pressing the trigger is considered to be initiated first, and then the arm is pushed to pierce the surface. After initiation, both pressing and pushing needs to happen together to drill the hole.

The `repeated` property denotes whether the activity needs to be reinstantiated to complete the skill. An activity is considered completed once its goal is achieved. For example, the activity "carrying an object" is completed when the worker reaches the destination location. So, it is considered to be executed only once. On the other hand, spraying liquid is generally performed by squeezing a spray trigger for some time. This activity is considered to be repeated during the skill execution.  

A skill can label an activity with another skill. In that case the `step` for that activity additionally contains the `variables` field providing the mapping required for the labeled skill.

### Activity Labels

Activity labels for the YouTube videos are in `activity_labels.json`. The file is organized by O*NET tasks and labeled videos for different construction occupations. The file format is as follows

```json
{
  "occupations": [
    {
      "name": "NAME",
      "non_movement_tasks": [
        "NON_MOVEMENT_TASK_1",
        "NON_MOVEMENT_TASK_2"
      ],
      "movement_tasks": {
        "onet_tasks": [
          "MOVEMENT_TASK_1",
          "MOVEMENT_TASK_2"
        ],
        "videos": [
          "VIDEO_1",
          "VIDEO_2"
        ]
      }
    }
  ]
}
```

**Non-movement Tasks:** If a `task` in an occupation does not require movement, its distinct activities are identified directly from the task statement and each activity is labeled with a primitive action from the `information_processing` or `communication` class. These tasks do not have corresponding task videos. Most contain one activity, but a task that spans multiple primitive actions contains multiple entries in the `activities` list. It has the following format

```json
{
  "onet_task_number": "NUMBER",
  "onet_task": "TASK_DESCRIPTION",
  "activities": [
    {
      "activity": "ACTIVITY_DESCRIPTION",
      "activity_short": "ACTIVITY_SHORT_DESCRIPTION",
      "category": "PRIMITIVE"
    }
  ]
}
```

Because these activities are inferred from the task statement rather than a
video, they do not contain `variables`, `repeated`, or `segment` properties.

**Movement Tasks:** If a `task` in an `occupation` requires movement, the `onet_tasks` property contains onet task number, descriptions and mapped video IDs and the `videos` property contains mapping to onet tasks and labels of the video segments. It has the following format-

```json
{
  "onet_tasks": [
    {
      "onet_task_number": 1,
      "onet_task": "TASK_DESCRIPTION",
      "task_videos": [1, 2]
    }
  ],
  "videos": [
    {
      "id": 1,
      "video_name": "NAME",
      "video_url": "URL",
      "length": 100,
      "mapped_tasks": [1, 2],
      "tools": ["TOOL_1", "TOOL_2"],
      "activities": [
        {
          "activity": "ACTIVITY_DESCRIPION",
          "activity_short": "ACTIVITY_SHORT_DESCRIPTION",
          "category": "PRIMITIVE_OR_SKILL",
          "variables": {
            "variable_1": "item_1",
            "variable_2": "item_2"
          },
          "repeated": "BOOLEAN_TYPE",
          "segment": "MM:SS - MM:SS"
        }
      ]
    }
  ]
}
```

Notes

- **length**: Video length in seconds.
- **activity**: If the `activity` is labeled as a primitive action, then the "variables" property is `{}`.
- **variables**: The `variables` property denotes an item used in the activity. With this `variables` property, all `variables` listed in a skill is mapped to the actual item used in the activity.
- **repeated**: If the activity is performed only once before transitioning to other acitivities, then the `repeated` property is marked as `false`. If the activity is executed repeatedly for this task, by itself or as part of a group of activities, then this property is marked as `true`. If the activity is a skill, then repetation of the whole skill is considered.
- **segment**: The `segment` denotes the timestamp in the video where the activity happens (including repeatation of the activity).

### Tools

`tools.json` contains a list of construction tools used in the videos that are labeled. It has the following format

```json
{
  "tools": ["TOOL_1", "TOOL_2"]
}
```
