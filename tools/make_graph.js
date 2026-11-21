// node tools/make_graph.js song.mp3 out.json [--ffmpeg path] [--learned]   builds the same graph the web page builds
const { spawnSync } = require('child_process'), fs = require('fs'), A = require('../analyze.js');
const [src, out] = process.argv.slice(2, 4), i = process.argv.indexOf('--ffmpeg'), ff = i > 0 ? process.argv[i + 1] : 'ffmpeg';
const r = spawnSync(ff, ['-v', 'error', '-i', src, '-ac', '1', '-ar', String(A.SR), '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
if (r.status !== 0) { console.error('ffmpeg failed'); process.exit(1); }
const y = new Float32Array(r.stdout.buffer, r.stdout.byteOffset, r.stdout.length / 4);
A.build(y, { model: process.argv.includes('--learned') ? require('../continuity_model.js') : null, style: process.argv.includes('--eternal') ? 'eternal' : undefined, eternalSmooth: process.argv.includes('--eternal') }).then(g => { fs.writeFileSync(out, JSON.stringify(g)); console.log(`${g.beats} beats @ ${g.bpm} BPM, ${g.edges.length} jumps -> ${out}`); });
