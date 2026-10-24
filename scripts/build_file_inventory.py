"""Document staged files and verify a downloaded branch without needing Git."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT/'PROJECT_FILES.json'


def purpose(path):
    name = Path(path).name
    if path.startswith('assets/panda/'):
        return 'Franka Panda 模型、网格、上游说明/许可证或下载清单'
    if path.startswith('assets/ycb/'):
        return '六种 YCB 物体的模型、纹理、碰撞部件或上游许可证'
    if path.startswith('assets/'):
        return '固定模型来源版本及逐文件 SHA-256 校验值'
    if path.startswith('deliverables/editing_materials/'):
        return '独立原速剪辑素材、配套分析/日志或素材哈希清单'
    if path.startswith('deliverables/'):
        return '演示/提交成品或交付物导航，具体版本与用途见 deliverables/README.md'
    if path.startswith('outputs/'):
        return '原始实验、开发诊断或录制中间素材；分类见 outputs/README.md'
    if path.startswith('docs/validation/'):
        return '按版本保留的实验/开发验证证据，包含失败而非只保留成功'
    if path.startswith('docs/images/'):
        return '报告及讲解用的实际仿真截图、数据曲线或点云图'
    if path.startswith(('docs/report/', 'output/pdf/')):
        return '报告 PDF；最新报告位于 output/pdf，旧版本报告位于 docs/report'
    if path.startswith(('robot_manipulation/', 'exploration/', 'scripts/', 'tests/')):
        return 'Python 模块/工具/测试；逐文件中文说明见 docs/FILE_GUIDE.md#源码与工具'
    if name.startswith('requirements'):
        return 'Python 依赖版本清单；按核心仿真、视频和报告分开安装'
    if path.startswith('.github/workflows/'):
        return 'GitHub Actions 自动验证配置'
    if path.startswith('.github/'):
        return 'GitHub PR 模板及项目协作配置'
    return '项目入口、使用/维护说明或 Git 配置；中文说明见 README.md 与 docs/FILE_GUIDE.md'


def staged_inventory():
    raw = subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT)
    files = []
    for record in raw.split(b'\0'):
        if not record: continue
        metadata,path = record.split(b'\t',1)
        mode,oid,stage = metadata.decode().split()
        path = path.decode('utf-8')
        if path == 'PROJECT_FILES.json': continue
        if stage != '0' or mode not in ('100644','100755'):
            raise ValueError('Unmerged or unsupported index entry: '+path)
        files.append((path,oid))
    names = '\0'.join(path for path,_ in files)+'\0'
    attr_raw = subprocess.check_output(['git','check-attr','-z','--stdin','text'],
                         cwd=ROOT,input=names.encode('utf-8')).split(b'\0')
    attrs = {attr_raw[i].decode('utf-8'):attr_raw[i+2].decode()
             for i in range(0,len(attr_raw)-1,3)}
    process = subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,
                               stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    rows = []; cache = {}
    try:
        for path,oid in sorted(files):
            if oid not in cache:
                process.stdin.write((oid+'\n').encode());process.stdin.flush()
                actual,kind,size = process.stdout.readline().split()
                if actual.decode()!=oid or kind!=b'blob':raise ValueError('Invalid Git blob')
                data = process.stdout.read(int(size))
                if len(data)!=int(size) or process.stdout.read(1)!=b'\n':raise ValueError('Truncated Git blob')
                cache[oid] = (len(data),hashlib.sha256(data).hexdigest(),b'\0' not in data)
            size,digest,is_text = cache[oid]
            normalization = 'lf' if attrs[path]=='set' or (attrs[path]=='auto' and is_text) else 'none'
            rows.append({'path':path,'bytes_in_git':size,'sha256':digest,
                         'normalization':normalization,'purpose':purpose(path)})
    finally:
        process.stdin.close();process.stdout.close()
        if process.wait()!=0:raise RuntimeError('git cat-file failed')
    return {'schema_version':1,'scope':'Every staged branch file except this self-referential manifest',
            'text_hashing':'LF canonicalization only when normalization=lf; other files use exact bytes',
            'file_count':len(rows),'total_bytes_in_git':sum(r['bytes_in_git'] for r in rows),'files':rows}


def verify_files(manifest):
    for row in manifest['files']:
        path = (ROOT/row['path']).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Path leaves project')
        data = path.read_bytes()
        if row['normalization']=='lf':data=data.replace(b'\r\n',b'\n')
        if len(data)!=row['bytes_in_git'] or hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('File content mismatch: '+row['path'])
    print(f"Verified {manifest['file_count']} files, including exact model/video/archive bytes")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group()
    action.add_argument('--check',action='store_true',help='Compare the saved manifest with the current Git index')
    action.add_argument('--verify-files',action='store_true',help='Verify working files; usable without Git after downloading ZIP')
    args=parser.parse_args()
    if args.verify_files:
        verify_files(json.loads(MANIFEST.read_text(encoding='utf-8')))
        return
    manifest=staged_inventory()
    if args.check:
        if json.loads(MANIFEST.read_text(encoding='utf-8'))!=manifest:raise ValueError('Stale PROJECT_FILES.json')
        print('Inventory matches Git index')
    else:
        MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"Indexed {manifest['file_count']} files, {manifest['total_bytes_in_git']/1e6:.1f} MB")


if __name__=='__main__':main()
