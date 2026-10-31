import { describe, expect, it } from "vitest";
import { buildRunnerScript } from "./CodeSandbox";

describe("buildRunnerScript", () => {
  it("оборачивает код ученика: stdout перехват, ошибка не роняет хост", () => {
    const script = buildRunnerScript();
    expect(script).toContain("exec(compile(__student_code");
    expect(script).toContain("io.StringIO()");
    expect(script).toContain("traceback.format_exc");
    expect(script).toContain("json.dumps(_result)");
    // stdout возвращается под контролем: системный восстанавливается
    expect(script).toContain("sys.stdout = _real_stdout");
  });

  it("не содержит подстановки кода ученика (код передаётся через globals)", () => {
    const script = buildRunnerScript();
    expect(script).not.toContain('print("');
    expect(script).toContain("__student_code");
  });
});
