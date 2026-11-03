#!/usr/bin/env python3
"""Generate the fixed-output OCI test layout with exactly 640 worker operations."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile

EXPECTED = 'e0e1ca9321c42adfff1f7e9fe490a5750310b89bf9a9b0b577dcef9563ec57a7'


def main(fixture, root):
    data = fixture.read_bytes()
    assert len(data) == 320000 and hashlib.sha256(data).hexdigest() == EXPECTED
    root.mkdir(mode=0o700, parents=False, exist_ok=False)
    blobs = root / 'blobs/sha256'; blobs.mkdir(parents=True)
    def blob(content):
        digest = hashlib.sha256(content).hexdigest()
        (blobs / digest).write_bytes(content)
        return 'sha256:' + digest
    def encode(value):
        return json.dumps(value, separators=(',', ':')).encode()
    image = io.BytesIO()
    with tarfile.open(fileobj=image, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        for i in range(128):
            payload = data if i == 0 else b''
            entry = tarfile.TarInfo('app' if i == 0 else f'f{i:03d}')
            entry.size, entry.mode, entry.uid, entry.gid, entry.mtime = len(payload), 0o755 if i == 0 else 0o644, 0, 0, 0
            archive.addfile(entry, io.BytesIO(payload))
    layer = image.getvalue(); layer_digest = blob(layer)
    config = encode({'architecture':'arm64','os':'linux','rootfs':{'type':'layers','diff_ids':[layer_digest]*4},
                     'config':{'Entrypoint':['/app'],'Cmd':[],'Env':[],'WorkingDir':'/'}})
    config_digest = blob(config)
    manifest = encode({'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json',
                       'config':{'mediaType':'application/vnd.oci.image.config.v1+json','digest':config_digest,'size':len(config)},
                       'layers':[{'mediaType':'application/vnd.oci.image.layer.v1.tar','digest':layer_digest,'size':len(layer)} for _ in range(4)]})
    manifest_digest = blob(manifest)
    (root/'oci-layout').write_text('{"imageLayoutVersion":"1.0.0"}')
    (root/'index.json').write_bytes(encode({'schemaVersion':2,'manifests':[{'mediaType':'application/vnd.oci.image.manifest.v1+json',
                                                                           'digest':manifest_digest,'size':len(manifest)}]}))
    print(manifest_digest)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();main(a.fixture.resolve(),a.output.resolve())
