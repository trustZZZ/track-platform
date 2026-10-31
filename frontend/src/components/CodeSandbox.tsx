// Pyodide-песочница (этап E4): запуск кода L1-задач в браузере (WASM).
// Python грузится с CDN один раз; серверу уходит только отметка (kind=pyodide).
import { useRef, useState } from "react";
import { submitTask } from "../api/client";
import { MeResponse } from "../api/client";

const PYODIDE_VERSION = "0.26.4";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/pyodide.js`;

/** Python-обёртка: исполняет код ученика, собирает stdout/ошибку, возвращает JSON. */
export function buildRunnerScript(): string {
  return `
import io, sys, json, traceback
_result = {"stdout": "", "ok": False, "error": None}
_buf = io.StringIO()
_real_stdout = sys.stdout
sys.stdout = _buf
try:
    exec(compile(__student_code, "<student>", "exec"), {"__name__": "__main__"})
    _result["ok"] = True
except Exception:
    _result["error"] = traceback.format_exc(limit=3)
finally:
    sys.stdout = _real_stdout
_result["stdout"] = _buf.getvalue()
json.dumps(_result)
`;
}

interface PyodideInterface {
  globals: { set: (name: string, value: unknown) => void };
  runPythonAsync: (code: string) => Promise<string>;
}

declare global {
  interface Window {
    loadPyodide?: (options: { indexURL: string }) => Promise<PyodideInterface>;
  }
}

let pyodidePromise: Promise<PyodideInterface> | null = null;

function loadPyodideOnce(): Promise<PyodideInterface> {
  if (pyodidePromise) {
    return pyodidePromise;
  }
  pyodidePromise = new Promise<PyodideInterface>((resolve, reject) => {
    const indexURL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
    const existing = window.loadPyodide;
    if (existing) {
      resolve(existing({ indexURL }));
      return;
    }
    const script = document.createElement("script");
    script.src = PYODIDE_CDN;
    script.onload = () => {
      if (window.loadPyodide) {
        resolve(window.loadPyodide({ indexURL }));
      } else {
        reject(new Error("Pyodide не загрузился"));
      }
    };
    script.onerror = () => reject(new Error("CDN Pyodide недоступен"));
    document.head.appendChild(script);
  });
  return pyodidePromise;
}

interface RunResult {
  ok: boolean;
  stdout: string;
  error: string | null;
}

export function CodeSandbox({
  lessonId,
  me,
}: {
  lessonId: string;
  me: MeResponse | null;
}) {
  const [code, setCode] = useState('print("Привет, трек!")');
  const [output, setOutput] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const pyodideRef = useRef<PyodideInterface | null>(null);

  async function run() {
    setBusy(true);
    setOutput("Запуск (первый запуск загружает Python ~10 МБ)...");
    try {
      const pyodide = await loadPyodideOnce();
      pyodideRef.current = pyodide;
      setLoaded(true);
      pyodide.globals.set("__student_code", code);
      const raw = (await pyodide.runPythonAsync(buildRunnerScript())) as string;
      const result = JSON.parse(raw) as RunResult;
      const parts = [result.stdout];
      if (result.error) {
        parts.push(`ОШИБКА:\n${result.error}`);
      }
      parts.push(result.ok ? "✓ Код выполнился" : "✗ Выполнение упало");
      setOutput(parts.join("\n").trim());
    } catch (e) {
      setOutput(e instanceof Error ? e.message : "Ошибка запуска");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit() {
    setBusy(true);
    try {
      await submitTask({
        lesson_id: lessonId,
        task_id: `${lessonId}:sandbox`,
        kind: "pyodide",
      });
      setSubmitted(true);
    } catch (e) {
      setOutput(e instanceof Error ? e.message : "Ошибка отправки");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section style={{ marginTop: 24, border: "1px solid #ddd", padding: 12 }}>
      <h3>Песочница Python (в браузере)</h3>
      <p>
        <small>
          Код выполняется локально в вашем браузере (Pyodide/WASM) — безопасно и
          без сервера. Напишите решение задачи и нажмите «Запустить».
        </small>
      </p>
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={8}
        style={{ width: "100%", fontFamily: "monospace" }}
        spellCheck={false}
      />
      <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
        <button onClick={run} disabled={busy}>
          {busy ? "..." : loaded ? "Запустить" : "Запустить (загрузить Python)"}
        </button>
        {me && (
          <button onClick={handleSubmit} disabled={busy || submitted}>
            {submitted ? "Задача засчитана ✔" : "Отправить задачу"}
          </button>
        )}
      </div>
      {output && (
        <pre
          style={{
            background: "#f6f6f6",
            padding: 8,
            marginTop: 8,
            whiteSpace: "pre-wrap",
          }}
        >
          {output}
        </pre>
      )}
    </section>
  );
}
