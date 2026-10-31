import { afterEach, describe, expect, it, vi } from "vitest";
import {
  completeLesson,
  echoMessage,
  getCatalog,
  getHealth,
  getLesson,
  getLessons,
  getMe,
} from "./client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("getHealth парсит ответ и проверяет статус", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", app: "test", version: "0.1.0" }),
      }),
    );
    const data = await getHealth();
    expect(data.status).toBe("ok");
  });

  it("echoMessage шлёт POST с JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ echo: { message: "hi" } }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const data = await echoMessage({ message: "hi" });
    expect(data).toEqual({ echo: { message: "hi" } });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/echo");
    expect(init.method).toBe("POST");
  });

  it("бросает ошибку при !ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500 }),
    );
    await expect(getHealth()).rejects.toThrow(/500/);
  });

  // --- Контент (E2) ---

  it("getCatalog читает уровни трека", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [{ level: "L2", modules: [] }],
      }),
    );
    const data = await getCatalog();
    expect(data[0].level).toBe("L2");
    expect(data[0].modules).toEqual([]);
  });

  it("getLessons возвращает список без тел", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => [
          { id: "lesson-L2-M1-01", title: "Хранилище рекордов", skills: [] },
        ],
      }),
    );
    const data = await getLessons();
    expect(data[0].id).toBe("lesson-L2-M1-01");
  });

  it("getLesson кодирует id и возвращает тело", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ id: "lesson-L2-M1-01", body: "# Урок" }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const data = await getLesson("lesson-L2-M1-01");
    expect(data.body).toContain("Урок");
    expect(fetchMock.mock.calls[0][0]).toContain("/v1/lessons/lesson-L2-M1-01");
  });

  // --- Прогресс (E3) ---

  it("getMe прокидывает 401 как ошибку", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 401 }),
    );
    await expect(getMe()).rejects.toThrow(/401/);
  });

  it("completeLesson шлёт POST на /progress/{id}/complete", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ lesson_id: "lesson-X", completed: true }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const data = await completeLesson("lesson-X");
    expect(data.completed).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain(
      "/v1/progress/lesson-X/complete",
    );
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
  });
});
