# Third-party assets and provenance

The project uses the third-party assets below. Their original notices are retained in the offline submission and the complete delivery branch, which now also contains the pinned models and textures at the user's request. Public availability of this project does not transfer ownership of these assets to the project team.

| Asset | Source and revision | Notice / attribution |
|---|---|---|
| Franka Panda model | [Google DeepMind MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie), commit `0059d4335f8156206f63a35662313385f7ad6d74` | Original `assets/panda/LICENSE` and model README are bundled. |
| YCB geometry and texture data | Yale-CMU-Berkeley Object and Model Set; B. Calli, A. Walsman, A. Singh, S. Srinivasa, P. Abbeel and A. M. Dollar, [2015 paper](https://arxiv.org/abs/1502.03143) | Dataset attribution is recorded as CC BY 4.0 in `assets/ycb.lock.json`; original data source: [YCB dataset](https://ycb-benchmarks.s3.amazonaws.com/index.html). |
| MuJoCo conversion of YCB subset | [elpis-lab/YCB_Dataset](https://github.com/elpis-lab/YCB_Dataset), commit `9e8c6488a2ff673d9aa48a91492fb89423c1b106` | MIT conversion notice retained in `assets/ycb/LICENSE`, with its original README. |
| Simulation platform | [MuJoCo documentation](https://mujoco.readthedocs.io/en/stable/overview.html) | Installed runtime dependency; its distribution is governed by its own license. |

The six YCB models are gelatin box, pudding box, tomato soup can, lemon, strawberry and foam brick. Runtime transparency removes the selected target's printed texture and changes its display alpha; this is a derived visualization, not new glass data. Physical scale, mass and contact properties are retained.

Every downloaded model file is checked against the SHA-256 lock files. The final ZIP includes a second `SUBMISSION_MANIFEST.json` for the complete delivered contents. The original course slides remain outside the repository and are not included in the ZIP.
