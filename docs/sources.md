# Local reference index

These materials suffice for the initial initialization/communication case; no
additional repository is needed now. Raw clones stay under ignored
references/repos/. This index and manifest are versioned for provenance.
The robotics projects have not been installed, compiled or run.

## Versions and reproduction

[source_manifest.json](source_manifest.json) records exact branches/commits,
selected-file SHA-256, license fingerprints and commit-pinned GitHub links.
It describes local snapshots, not necessarily the online website build.
dirty=true means tracked files were modified; pinned links may differ from
local bytes and need comparison.

Preserve the current manifest before repository updates. After choosing a new
knowledge baseline, run `python scripts/inventory_sources.py` and review version/
knowledge changes. The script does not fetch, pull or modify repositories.
Hashes describe local bytes and may reflect Git newline conversion.

## Repository roles

| Repository | Priority | Use |
| --- | --- | --- |
| docs | Initial | FCI overview, troubleshooting, compatibility pages/data and website sources |
| libfranka | Initial | Networking, preparation, compatibility and installation background |
| franka_ros2 | Initial, Jazzy material only | Startup arguments, robot address, fake hardware and controller startup |
| franka_description | Later | Model/component relationships; no initial model/mesh import needed |
| labs | Deferred | Data collection/orchestration beyond current investigation scope |
| libfranka-common | Supporting | Shared protocol types, handshake versions and state; no binary implementation |

## Initial source mapping and reading order

Paths are project-relative. Website links aid reading; the manifest's local commit
defines the knowledge baseline.

| Source ID | Topic/local file | Reading entry | Knowledge destination |
| --- | --- | --- | --- |
| FCI-OVERVIEW | references/repos/docs/source/overview.rst | [FCI Overview](https://frankarobotics.github.io/docs/overview.html) | knowledge/00_overview/ |
| FCI-TROUBLESHOOTING | references/repos/docs/source/troubleshooting.rst | [Troubleshooting](https://frankarobotics.github.io/docs/troubleshooting.html) | knowledge/30_troubleshooting/ |
| LIBFRANKA-NETWORK | references/repos/libfranka/docs/system_requirements.rst | [Source](../references/repos/libfranka/docs/system_requirements.rst) | knowledge/10_configuration/ |
| LIBFRANKA-SETUP | references/repos/libfranka/docs/getting_started.rst | [Source](../references/repos/libfranka/docs/getting_started.rst) | knowledge/20_procedures/ |
| LIBFRANKA-COMPATIBILITY | references/repos/libfranka/docs/compatibility_matrix.rst | [Source](../references/repos/libfranka/docs/compatibility_matrix.rst) | knowledge/10_configuration/ |
| FCI-COMPATIBILITY | references/repos/docs/source/compatibility.rst and _static/compatibility_data.py | [Compatibility](https://frankarobotics.github.io/docs/compatibility.html) | knowledge/10_configuration/ |
| ROS2-SETUP | references/repos/franka_ros2/README.md | [README](../references/repos/franka_ros2/README.md) | knowledge/10_configuration/ |
| ROS2-BRINGUP | references/repos/franka_ros2/franka_bringup/doc/index.rst | [Bring-up](../references/repos/franka_ros2/franka_bringup/doc/index.rst) | knowledge/20_procedures/ |
| ROS2-CONFIG | references/repos/franka_ros2/franka_bringup/config/franka.config.yaml and launch/franka.launch.py | [Config](../references/repos/franka_ros2/franka_bringup/config/franka.config.yaml) | knowledge/10_configuration/ |
| ROS2-JOINT-IMPEDANCE | references/repos/franka_ros2/franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp, update() | [Controller](../references/repos/franka_ros2/franka_example_controllers/src/fr3/joint_impedance_example_controller.cpp) | Conceptual motion background, not vendor-controller reproduction |
| FCI-PROTOCOL-TYPES | references/repos/libfranka-common/include/research_interface/robot/service_types.h, rbk_types.h and gripper/types.h | [Repository](../references/repos/libfranka-common/README.md) | Protocol/state background, not direct source indexing |

Example configuration and launch defaults may differ; a single example does not
prove runtime configuration. Preserve ROS 1/ROS 2 Jazzy/Humble and Panda/FR3 scope.
Do not merge different compatibility tables without checking applicability.

## What to extract first

1. Distinguish Connection timeout, Robot is not reachable, UDP receive: Timeout
   and Incompatible Library Version in FCI-TROUBLESHOOTING. Preserve exact error
   strings and section anchors.
2. Extract required context: model, system/client version, configured address,
   connection location, FCI state and full error.
3. Establish cited compatibility rules; mark independently invented demo versions synthetic.
4. Distinguish bring-up configuration, actual connections and fake hardware,
   avoiding claims that simulation validates physical communication.

## Knowledge curation rules

- Begin with overview, versions/configuration, initialization procedure,
  connection troubleshooting and ticket rules.
- Use unique doc_id and version/status/source_type/applies_to/source_ids;
  cite original sections.
- Separate vendor facts, project interpretation and synthetic rules.
  Project-authored ticket/escalation rules are not Franka instructions.
- Check repository LICENSE/NOTICE and file-level declarations. This index does
  not authorize bulk copying. Preserve applicable attribution, licensing and
  modification notices when copying/adapting.
- Do not index entire repositories, evaluation answers or scenario causes.
  Runtime state comes from tools; expectations belong in evaluation/cases/.
- Initialization covers connection/configuration/evidence. Motion separately
  covers offline PD and interpretation. No automatic safety changes, real
  movement or real-time kernel configuration.

## Material preparation

[demo_bench.md](demo_bench.md) defines composition and readable fields. The initial
next step was five knowledge categories and three synthetic states. This index
establishes a source baseline rather than proving source projects work;
implemented materials are described in the project README.

## Language and ownership

Keep cloned/downloaded third-party files unchanged, including their original
language. English-by-default applies to project-generated/maintained material,
not these reference repositories.
