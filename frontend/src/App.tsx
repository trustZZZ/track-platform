import { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import { marked } from "marked";
import {
  CatalogLevel,
  LessonFull,
  LessonSummary,
  MeResponse,
  ModuleOverview,
  Portfolio,
  RouterAnswer,
  RouterResult,
  RouterTask,
  claimBadges,
  completeLesson,
  getCatalog,
  getLesson,
  getLessons,
  getMe,
  getModule,
  getPortfolio,
  getRouterTasks,
  logout,
  submitRouter,
} from "./api/client";
import { CodeSandbox } from "./components/CodeSandbox";

// --- Простой hash-роутинг (без зависимости react-router в MVP) ---

type Route =
  | { name: "catalog" }
  | { name: "lesson"; id: string }
  | { name: "module"; id: string }
  | { name: "router" }
  | { name: "portfolio" };

function parseRoute(): Route {
  const hash = window.location.hash;
  const lessonMatch = hash.match(/^#\/lesson\/(.+)$/);
  if (lessonMatch) {
    return { name: "lesson", id: decodeURIComponent(lessonMatch[1]) };
  }
  const moduleMatch = hash.match(/^#\/module\/(.+)$/);
  if (moduleMatch) {
    return { name: "module", id: decodeURIComponent(moduleMatch[1]) };
  }
  if (hash === "#/router") {
    return { name: "router" };
  }
  if (hash === "#/portfolio") {
    return { name: "portfolio" };
  }
  return { name: "catalog" };
}

function navigate(route: Route): void {
  window.location.hash = route.name === "catalog" ? "#/" : `#/${route.name}`;
}

// --- Каталог ---

function Catalog({
  onOpenLesson,
  onOpenModule,
}: {
  onOpenLesson: (id: string) => void;
  onOpenModule: (id: string) => void;
}) {
  const [levels, setLevels] = useState<CatalogLevel[] | null>(null);
  const [lessons, setLessons] = useState<LessonSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getCatalog(), getLessons()])
      .then(([catalog, allLessons]) => {
        setLevels(catalog);
        setLessons(allLessons);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Ошибка загрузки"),
      );
  }, []);

  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!levels || !lessons) return <p>Загрузка каталога...</p>;

  return (
    <section>
      {levels.map((level) => (
        <article key={level.level} style={{ marginBottom: 24 }}>
          <h2>Пролёт {level.level}</h2>
          {level.modules.map((module) => {
            const moduleLessons = lessons.filter(
              (lesson) =>
                lesson.level === level.level && lesson.module === module.module,
            );
            return (
              <div
                key={module.module}
                style={{
                  border: "1px solid #ddd",
                  padding: 12,
                  marginBottom: 12,
                }}
              >
                <h3>
                  {module.id ? (
                    <a
                      href={`#/module/${encodeURIComponent(module.id)}`}
                      onClick={(e) => {
                        e.preventDefault();
                        onOpenModule(module.id as string);
                      }}
                    >
                      {module.module}
                    </a>
                  ) : (
                    <span>{module.module}</span>
                  )}{" "}
                  — {module.title || "обзор модуля"}{" "}
                  <small>
                    (~{module.lessons || moduleLessons.length} ур.,{" "}
                    {module.time_est_min} мин)
                  </small>
                </h3>
                {moduleLessons.length === 0 && (
                  <p>
                    <small>
                      Уроки модуля дописываются — откройте обзор по ссылке выше.
                    </small>
                  </p>
                )}
                <ul>
                  {moduleLessons.map((lesson) => (
                    <li key={lesson.id}>
                      <a
                        href={`#/lesson/${encodeURIComponent(lesson.id)}`}
                        onClick={(e) => {
                          e.preventDefault();
                          onOpenLesson(lesson.id);
                        }}
                      >
                        {lesson.title}
                      </a>{" "}
                      <small>({lesson.time_est_min} мин)</small>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </article>
      ))}
    </section>
  );
}

// --- Страница урока ---

function LessonPage({
  id,
  me,
  onCompleted,
}: {
  id: string;
  me: MeResponse | null;
  onCompleted: (lessonId: string) => void;
}) {
  const [lesson, setLesson] = useState<LessonFull | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setLesson(null);
    setError(null);
    getLesson(id)
      .then(setLesson)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Ошибка загрузки урока"),
      );
  }, [id]);

  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!lesson) return <p>Загрузка урока...</p>;

  const completed = me?.completed_lessons.includes(lesson.id) ?? false;

  async function handleComplete() {
    const current = lesson;
    if (!current) return;
    setBusy(true);
    setNotice(null);
    try {
      await completeLesson(current.id);
      onCompleted(current.id);
      setNotice("Урок отмечен как пройденный ✔");
    } catch (e) {
      setNotice(
        e instanceof Error && e.message.includes("401")
          ? "Войдите через GitHub, чтобы сохранять прогресс"
          : e instanceof Error
            ? e.message
            : "Ошибка отметки",
      );
    } finally {
      setBusy(false);
    }
  }

  const html = DOMPurify.sanitize(marked.parse(lesson.body, { async: false }));

  return (
    <section>
      <p>
        <a
          href="#/"
          onClick={(e) => {
            e.preventDefault();
            navigate({ name: "catalog" });
          }}
        >
          ← Каталог
        </a>
      </p>
      <h1>{lesson.title}</h1>
      <p>
        <small>
          {lesson.level} · модуль {lesson.module} · {lesson.time_est_min} мин ·{" "}
          навыки: {lesson.skills.join(", ")}
        </small>
      </p>
      {completed && <p style={{ color: "green" }}>Пройден ✔</p>}
      {me ? (
        <button onClick={handleComplete} disabled={busy || completed}>
          {completed ? "Урок пройден" : "Отметить урок пройденным"}
        </button>
      ) : (
        <p>
          <small>Войдите через GitHub, чтобы сохранять прогресс.</small>
        </p>
      )}
      {notice && <p>{notice}</p>}
      <hr />
      {/* Тело урока — markdown из content.json, санитизирован DOMPurify */}
      <div className="lesson-body" dangerouslySetInnerHTML={{ __html: html }} />
      {/* Этап E4: L1-задачи — песочница Pyodide в браузере */}
      {lesson.level === "L1" && <CodeSandbox lessonId={lesson.id} me={me} />}
    </section>
  );
}

// --- Портфолио (этап E6) ---

function PortfolioPage({ me }: { me: MeResponse | null }) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) return;
    getPortfolio()
      .then(setPortfolio)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Ошибка загрузки портфолио"),
      );
  }, [me]);

  if (!me) {
    return (
      <section>
        <p>
          <a
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              navigate({ name: "catalog" });
            }}
          >
            ← Каталог
          </a>
        </p>
        <p>Портфолио доступно после входа через GitHub (ссылка в шапке).</p>
      </section>
    );
  }
  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!portfolio) return <p>Загрузка портфолио...</p>;

  return (
    <section>
      <p>
        <a
          href="#/"
          onClick={(e) => {
            e.preventDefault();
            navigate({ name: "catalog" });
          }}
        >
          ← Каталог
        </a>
      </p>
      <h1>Портфолио: {portfolio.login}</h1>
      <p>
        Профиль GitHub:{" "}
        <a href={portfolio.github_url} target="_blank" rel="noreferrer">
          {portfolio.github_url}
        </a>
      </p>
      <h2>Прогресс по пролётам</h2>
      <ul>
        {portfolio.levels.map((level) => (
          <li key={level.level}>
            Пролёт {level.level}: {level.done} из {level.total} уроков
          </li>
        ))}
      </ul>
      <h2>Бейджи</h2>
      {portfolio.badges.length === 0 ? (
        <p>
          <small>
            Пока нет — пройдите все уроки пролёта, чтобы получить бейдж.
          </small>
        </p>
      ) : (
        <ul>
          {portfolio.badges.map((badge) => (
            <li key={badge}>🏅 {badge}</li>
          ))}
        </ul>
      )}
      <button
        onClick={async () => {
          const claimed = await claimBadges();
          if (claimed.granted.length > 0) {
            const refreshed = await getPortfolio();
            setPortfolio(refreshed);
          }
        }}
      >
        Проверить бейджи
      </button>
    </section>
  );
}

// --- Роутер-диагностика (этап E5) ---

function RouterPage() {
  const [tasks, setTasks] = useState<RouterTask[] | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [result, setResult] = useState<RouterResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getRouterTasks()
      .then(setTasks)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Ошибка загрузки анкеты"),
      );
  }, []);

  async function handleSubmit() {
    setBusy(true);
    setError(null);
    try {
      const answers: RouterAnswer[] = Object.entries(values)
        .filter(([, value]) => value.trim() !== "")
        .map(([task_id, value]) => ({ task_id, value: value.trim() }));
      setResult(await submitRouter(answers));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка проверки");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <p>
        <a
          href="#/"
          onClick={(e) => {
            e.preventDefault();
            navigate({ name: "catalog" });
          }}
        >
          ← Каталог
        </a>
      </p>
      <h1>Определение пролёта</h1>
      <p>
        <small>
          Три задачи порога Core (L2). Вход свободный: результат — рекомендация,
          выбор всегда за вами. Для сохранения результата войдите через GitHub.
        </small>
      </p>
      {error && <p style={{ color: "red" }}>{error}</p>}
      {tasks === null ? (
        <p>Загрузка анкеты...</p>
      ) : (
        <div>
          {tasks.map((task) => (
            <div key={task.task_id} style={{ marginBottom: 16 }}>
              <p>
                <strong>{task.topic}.</strong> {task.question}
              </p>
              <input
                value={values[task.task_id] ?? ""}
                onChange={(e) =>
                  setValues((prev) => ({
                    ...prev,
                    [task.task_id]: e.target.value,
                  }))
                }
                placeholder="Ответ числом"
                style={{ width: 200 }}
              />
            </div>
          ))}
          <button onClick={handleSubmit} disabled={busy}>
            Проверить и получить рекомендацию
          </button>
        </div>
      )}
      {result && (
        <div style={{ marginTop: 16, border: "1px solid #ccc", padding: 12 }}>
          <h2>
            Рекомендация: пролёт {result.recommended_level}
            {result.bridge ? ` (мост ${result.bridge})` : ""}
          </h2>
          <p>
            Верно {result.score} из {result.total}. {result.text}
          </p>
          <p>
            <small>
              {result.saved
                ? "Результат сохранён в вашем профиле."
                : "Результат не сохранён — войдите через GitHub, чтобы хранить историю."}
            </small>
          </p>
          <a
            href="#/"
            onClick={(e) => {
              e.preventDefault();
              navigate({ name: "catalog" });
            }}
          >
            Перейти в каталог
          </a>
        </div>
      )}
    </section>
  );
}

// --- Страница обзора модуля ---

function ModulePage({ id }: { id: string }) {
  const [module, setModule] = useState<ModuleOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setModule(null);
    setError(null);
    getModule(id)
      .then(setModule)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Ошибка загрузки обзора"),
      );
  }, [id]);

  if (error) return <p style={{ color: "red" }}>{error}</p>;
  if (!module) return <p>Загрузка обзора...</p>;

  const html = DOMPurify.sanitize(marked.parse(module.body, { async: false }));

  return (
    <section>
      <p>
        <a
          href="#/"
          onClick={(e) => {
            e.preventDefault();
            navigate({ name: "catalog" });
          }}
        >
          ← Каталог
        </a>
      </p>
      <h1>{module.title}</h1>
      <p>
        <small>
          {module.level} · модуль {module.module} · {module.time_est_min} мин
        </small>
      </p>
      <hr />
      {/* Обзор модуля — markdown из content.json, санитизирован DOMPurify */}
      <div className="lesson-body" dangerouslySetInnerHTML={{ __html: html }} />
    </section>
  );
}

// --- Корень ---

export function App() {
  const [route, setRoute] = useState<Route>(parseRoute);
  const [me, setMe] = useState<MeResponse | null>(null);

  useEffect(() => {
    const onHash = () => setRoute(parseRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);

  function markCompleted(lessonId: string) {
    setMe((prev) =>
      prev
        ? {
            ...prev,
            completed_lessons: [
              ...new Set([...prev.completed_lessons, lessonId]),
            ],
          }
        : prev,
    );
  }

  async function handleLogout() {
    await logout();
    window.location.reload();
  }

  return (
    <main
      style={{
        fontFamily: "system-ui",
        padding: 32,
        maxWidth: 760,
        margin: "0 auto",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1
          style={{ fontSize: 20, cursor: "pointer" }}
          onClick={() => navigate({ name: "catalog" })}
        >
          Python. Путь инженера — трек
        </h1>
        <span style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <a href="#/router">Определить пролёт</a>
          <a href="#/portfolio">Портфолио</a>
          {me ? (
            <span>
              {me.login} <button onClick={handleLogout}>Выйти</button>
            </span>
          ) : (
            <a href="/api/v1/auth/github/url">Войти через GitHub</a>
          )}
        </span>
      </header>
      <hr />
      {route.name === "catalog" ? (
        <Catalog
          onOpenLesson={(id) => navigate({ name: "lesson", id })}
          onOpenModule={(id) => navigate({ name: "module", id })}
        />
      ) : route.name === "router" ? (
        <RouterPage />
      ) : route.name === "portfolio" ? (
        <PortfolioPage me={me} />
      ) : route.name === "module" ? (
        <ModulePage id={route.id} />
      ) : (
        <LessonPage id={route.id} me={me} onCompleted={markCompleted} />
      )}
    </main>
  );
}
