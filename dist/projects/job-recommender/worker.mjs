let runtimePromise;

async function prepare() {
  self.postMessage({ type: 'progress', message: 'Loading Python. The first run can take a minute…' });
  const { loadPyodide } = await import('https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs');
  const runtime = await loadPyodide({ indexURL: 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/' });
  self.postMessage({ type: 'progress', message: 'Loading the original matching engine and data libraries…' });
  await runtime.loadPackage(['numpy', 'pandas', 'scikit-learn']);
  for (const filename of ['engine.py', 'bridge.py']) {
    const response = await fetch(new URL(filename, import.meta.url));
    if (!response.ok) throw new Error('The project engine could not be loaded. Please try again.');
    runtime.FS.writeFile(`/home/pyodide/${filename}`, await response.text(), { encoding: 'utf8' });
  }
  await runtime.runPythonAsync('from bridge import match_jobs');
  return runtime;
}

self.onmessage = async ({ data }) => {
  try {
    runtimePromise ||= prepare();
    const runtime = await runtimePromise;
    self.postMessage({ type: 'progress', message: 'Comparing your résumé with the job descriptions…' });
    runtime.globals.set('browser_payload', JSON.stringify(data.payload));
    const result = await runtime.runPythonAsync('match_jobs(browser_payload)');
    runtime.globals.delete('browser_payload');
    self.postMessage({ type: 'result', id: data.id, result: JSON.parse(result) });
  } catch (error) {
    const lines = String(error.message || error).trim().split('\n');
    self.postMessage({ type: 'error', id: data.id, message: lines.at(-1).replace(/^(ValueError|KeyError|RuntimeError):\s*/, '') });
  }
};
