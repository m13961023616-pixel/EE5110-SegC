"""Object catalog and portable asset adapter for the public YCB subset."""
from dataclasses import dataclass
import copy
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from .config import ROOT

YCB_OBJECTS = ('gelatin_box', 'pudding_box', 'tomato_soup_can', 'lemon', 'strawberry', 'foam_brick')


@dataclass
class ObjectModel:
    object_id: str
    vertices: np.ndarray
    mass: float
    xml_path: Path | None = None

    @property
    def bounds(self):
        return np.array([self.vertices.min(axis=0), self.vertices.max(axis=0)])

    @property
    def dimensions(self):
        return np.ptp(self.vertices, axis=0)


def load_object(name, config):
    if name == 'primitive_cube':
        half = config.object_size / 2
        vertices = np.array([[x, y, z] for x in (-half, half) for y in (-half, half) for z in (-half, half)])
        return ObjectModel(name, vertices, config.object_mass)
    if name not in YCB_OBJECTS:
        raise ValueError(f'Unknown object: {name}')
    path = ROOT / f'assets/ycb/ycb/{name}.xml'
    if not path.exists():
        raise FileNotFoundError('YCB assets missing. Run scripts/setup_ycb.py first.')
    root = ET.parse(path).getroot()
    mesh = root.find('asset/mesh')
    vertex_lines = (path.parent / mesh.get('file')).read_text(encoding='utf-8').splitlines()
    vertices = np.array([[float(v) for v in line.split()[1:4]] for line in vertex_lines if line.startswith('v ')])
    body = root.find('worldbody/body')
    visual = body.find('geom')
    vertices += np.fromstring(visual.get('pos', '0 0 0'), sep=' ')
    return ObjectModel(name, vertices, float(body.find('inertial').get('mass')), path)


def append_ycb(root, world, model):
    upstream = ET.parse(model.xml_path).getroot()
    assets = root.find('asset')
    for element in upstream.find('asset'):
        node = copy.deepcopy(element)
        if 'file' in node.attrib:
            node.set('file', str(model.xml_path.parent / node.get('file')))
        assets.append(node)
    body = copy.deepcopy(upstream.find('worldbody/body'))
    body.set('name', f'object_{model.object_id}')
    body.set('pos', '.48 0 .1')
    body.find('freejoint').set('name', f'object_free_{model.object_id}')
    # The upstream conversion uses fixed placeholder inertia 1e-3. Replace with
    # a mass-preserving bounding-box approximation, explicitly documented.
    dims = model.dimensions
    inertia = model.mass / 12 * np.array([dims[1]**2 + dims[2]**2,
                                         dims[0]**2 + dims[2]**2, dims[0]**2 + dims[1]**2])
    body.find('inertial').set('diaginertia', ' '.join(map(str, inertia)))
    for geom in body.findall('geom'):
        if geom.get('contype') == '0':
            geom.set('group', '2')
        else:
            geom.set('friction', '1.2 .01 .001')
            geom.set('condim', '6')
    world.append(body)
