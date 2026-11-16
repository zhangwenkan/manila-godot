"""Read shipped IL2CPP native code for ground construction; never execute it.

Writes research evidence only. Names come from metadata tokens matched to the
shipped Assembly-CSharp code generation module; function bounds come from PE
unwind records. Assembly output is not recovered official C# source.
"""
from pathlib import Path
import bisect
import json
import struct
import hashlib

import capstone
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP
import pefile

GAME = Path("D:/steam/steamapps/common/I Just Wanted to Fish Demo")
OUT = Path("demo/tropical_harbor_3d/captures/reference_style_audit_20261112")
META = GAME / "I Just Wanted to Fish_Data/il2cpp_data/Metadata/global-metadata.dat"
DLL = GAME / "GameAssembly.dll"


def main():
    meta = META.read_bytes()
    raw = DLL.read_bytes()
    pe = pefile.PE(data=raw, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXCEPTION"]])
    heap = meta[533796:2569084]

    def name(i):
        return heap[i:heap.find(b"\0", i)].decode("utf8", "replace") if i >= 0 else ""

    def fileoff(va):
        if not base <= va < base + pe.OPTIONAL_HEADER.SizeOfImage:
            raise ValueError(f"VA outside image: {va:x}")
        return pe.get_offset_from_rva(va - base)

    module_name = b"Assembly-CSharp.dll\0"
    candidates = []
    at = 0
    while True:
        found = raw.find(module_name, at)
        if found < 0:
            break
        at = found + 1
        va = base + pe.get_rva_from_offset(found)
        pointer = struct.pack("<Q", va)
        pos = 0
        while True:
            pos = raw.find(pointer, pos)
            if pos < 0:
                break
            try:
                count = struct.unpack_from("<I", raw, pos + 8)[0]
                table = struct.unpack_from("<Q", raw, pos + 16)[0]
                offset = fileoff(table)
                first = struct.unpack_from("<Q", raw, offset)[0]
                firstoff = fileoff(first)
                if 100 < count < 100000 and firstoff < len(raw):
                    candidates.append({"offset": pos, "count": count, "table_va": table})
            except (ValueError, struct.error, pefile.PEFormatError):
                pass
            pos += 1
    assert len(candidates) == 1, candidates
    module = candidates[0]
    pointers = struct.unpack_from("<" + "Q" * module["count"], raw, fileoff(module["table_va"]))
    methods = []
    aliases = {}
    # The Assembly-CSharp image range was independently identified in metadata.
    for k in range(4686, 5325):
        at = 9831536 + k * 76
        cls = name(struct.unpack_from("<i", meta, at)[0])
        start = struct.unpack_from("<i", meta, at + 24)[0]
        count = struct.unpack_from("<H", meta, at + 52)[0]
        for j in range(count):
            mo = 2947700 + (start + j) * 30
            method = name(struct.unpack_from("<i", meta, mo)[0])
            token = struct.unpack_from("<I", meta, mo + 18)[0]
            assert token >> 24 == 6, (cls, method, hex(token))
            index = (token & 0xFFFFFF) - 1
            assert 0 <= index < len(pointers), (cls, method, index)
            va = pointers[index]
            row = {"class": cls, "method": method, "token": hex(token), "va": va}
            methods.append(row)
            if va:
                aliases.setdefault(va, []).append(cls + "." + method)

    def unwind_root(begin, end, unwind, depth=0):
        assert depth < 16
        offset = pe.get_offset_from_rva(unwind)
        flags = raw[offset] >> 3
        count = raw[offset + 2]
        if flags & 4:  # UNW_FLAG_CHAININFO: a function can have several records.
            tail = offset + 4 + ((count + 1) & ~1) * 2
            return unwind_root(*struct.unpack_from("<III", raw, tail), depth + 1)
        return base + begin

    grouped_bounds = {}
    for entry in pe.DIRECTORY_ENTRY_EXCEPTION:
        p = entry.struct
        root = unwind_root(p.BeginAddress, p.EndAddress, p.UnwindData)
        grouped_bounds.setdefault(root, []).append((base + p.BeginAddress, base + p.EndAddress))
    bounds = sorted((base + x.struct.BeginAddress, base + x.struct.EndAddress) for x in pe.DIRECTORY_ENTRY_EXCEPTION)
    starts = [a for a, _ in bounds]
    method_starts = sorted(aliases)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    selected = {"TownSquare": None, "TownPaths": ["Upload", "Redraw", ".ctor", ".cctor"],
                "IslandGround": ["Ground", "Sand"], "DayNight": ["EnsureVolume", "ApplyVolume"]}
    results = []
    OUT.mkdir(exist_ok=True)
    for row in methods:
        if row["class"] not in selected:
            continue
        names = selected[row["class"]]
        if names is not None and row["method"] not in names:
            continue
        va = row["va"]
        bi = bisect.bisect_right(starts, va) - 1
        if va in grouped_bounds:
            ranges = []
            for a, b in sorted(grouped_bounds[va]):
                if ranges and ranges[-1][1] == a:
                    ranges[-1] = (ranges[-1][0], b)
                else:
                    ranges.append((a, b))
            end = max(b for a, b in ranges)
            bound_source = "PE unwind records including chained ranges"
        else:
            # Windows leaf functions may legitimately have no unwind entry.
            # Keep this weaker boundary explicit; do not label it an exact body.
            ni = bisect.bisect_right(method_starts, va)
            next_method = method_starts[ni] if ni < len(method_starts) else va + 4096
            ui = bisect.bisect_right(starts, va)
            next_unwind = starts[ui] if ui < len(starts) else va + 4096
            end = min(next_method, next_unwind, va + 4096)
            ranges = [(va, end)]
            bound_source = "leaf function bounded by next known entry (may include padding)"
        lines = [f"; {row['class']}.{row['method']} token {row['token']} VA {va:#x}",
                 "; Shipped native code, read-only disassembly; not original C# source."]
        calls = []
        constants = []
        instructions = []
        for a, b in ranges:
            body = raw[fileoff(a):fileoff(a) + b - a]
            instructions.extend(md.disasm(body, a))
        for ins in instructions:
            annotations = []
            if ins.mnemonic in ("call", "jmp") and ins.operands and ins.operands[0].type == X86_OP_IMM:
                dest = ins.operands[0].imm
                labels = aliases.get(dest, [])
                if labels:
                    annotations.append(" / ".join(labels))
                if ins.mnemonic == "call":
                    calls.append({"at": hex(ins.address), "target": hex(dest), "names": labels})
            if ins.mnemonic.endswith("ss") or ins.mnemonic in ("comiss", "ucomiss"):
                for op in ins.operands:
                    if op.type == X86_OP_MEM and op.mem.base == X86_REG_RIP and op.size == 4:
                        dest = ins.address + ins.size + op.mem.disp
                        try:
                            bits = raw[fileoff(dest):fileoff(dest) + 4]
                            val = struct.unpack("<f", bits)[0]
                            annotations.append(f"f32@{dest:#x}={val:.9g}")
                            constants.append({"at": hex(ins.address), "address": hex(dest), "value": val, "bits": bits.hex()})
                        except (ValueError, struct.error):
                            pass
            line = f"{ins.address:016x}  {ins.mnemonic:9} {ins.op_str}"
            if annotations:
                line += " ; " + "; ".join(annotations)
            lines.append(line)
        filename = row["class"] + "_" + row["method"].replace(".", "_").replace("<", "_").replace(">", "_").replace("|", "_") + ".native.asm.txt"
        (OUT / filename).write_text("\n".join(lines) + "\n", encoding="utf8")
        results.append({**row, "end_va": end, "bound_source": bound_source, "ranges": ranges, "bytes": sum(b-a for a,b in ranges), "assembly": filename, "calls": calls, "float_reads": constants})
    report = {"scope": "Read-only IL2CPP native analysis. File settings and method bodies do not prove a specific screenshot's runtime overrides.",
              "dll": str(DLL), "dll_sha256": hashlib.sha256(raw).hexdigest(),
              "metadata_sha256": hashlib.sha256(meta).hexdigest(), "module": module, "methods": results}
    (OUT / "ground_native_evidence.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
    print(json.dumps({"module": module, "methods": [{"name": r["class"] + "." + r["method"], "bytes": r["bytes"],
        "named_calls": sorted({n for c in r["calls"] for n in c["names"]}),
        "float_values": sorted({round(c["value"], 7) for c in r["float_reads"] if abs(c["value"]) < 10000})} for r in results]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
