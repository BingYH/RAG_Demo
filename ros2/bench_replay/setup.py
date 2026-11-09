from glob import glob
from setuptools import find_packages, setup

setup(name="bench_replay", version="0.1.0", packages=find_packages(),
      data_files=[("share/ament_index/resource_index/packages", ["resource/bench_replay"]),
                  ("share/bench_replay", ["package.xml"])] +
                 [("share/bench_replay/fixtures/" + name, glob("fixtures/" + name + "/*"))
                  for name in ("joint_tracking_baseline", "joint_tracking_oscillation", "joint_tracking_load_unknown")],
      install_requires=["setuptools"], zip_safe=True,
      maintainer="Demo maintainer", maintainer_email="demo@example.invalid",
      description="Synthetic ROS replay and HTTP capture", license="Apache-2.0",
      entry_points={"console_scripts": ["publisher = bench_replay.publisher:main", "collector = bench_replay.collector:main"]})
