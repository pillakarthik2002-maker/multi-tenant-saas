import { useCallback, useEffect, useState } from "react";
import {
  apiRequest,
  createCheckoutSession,
  getBillingStatus,
  login,
} from "./api";
import "./App.css";

const columns = [
  { id: "backlog", label: "Backlog" },
  { id: "todo", label: "To do" },
  { id: "in_progress", label: "In progress" },
  { id: "review", label: "In review" },
  { id: "done", label: "Done" },
];

function App() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [tenantId, setTenantId] = useState(
    sessionStorage.getItem("tenantId") || "1"
  );
  const [signedIn, setSignedIn] = useState(
    Boolean(sessionStorage.getItem("apiToken"))
  );
  const [boards, setBoards] = useState([]);
  const [boardId, setBoardId] = useState("");
  const [tasks, setTasks] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [billingLoading, setBillingLoading] = useState(false);
  const [billingStatus, setBillingStatus] = useState(null);
  const [activeTask, setActiveTask] = useState(null);
  const [comments, setComments] = useState([]);
  const [commentText, setCommentText] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileInputKey, setFileInputKey] = useState(0);

  const loadBoards = useCallback(async () => {
    const data = await apiRequest("/boards/");
    setBoards(data);

    if (data.length > 0) {
      const selectedBoard = data[0];
      setBoardId(String(selectedBoard.id));

      const boardTasks = await apiRequest(
        `/tasks/?board=${selectedBoard.id}`
      );
      setTasks(boardTasks);
    } else {
      setBoardId("");
      setTasks([]);
    }
  }, []);

  useEffect(() => {
    if (!signedIn) return;

    setLoading(true);
    setError("");

    Promise.all([loadBoards(), getBillingStatus()])
      .then(([, status]) => setBillingStatus(status))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [signedIn, loadBoards]);

  async function openTask(task) {
    setActiveTask(task);
    setComments([]);
    setAttachments([]);
    setCommentText("");
    setSelectedFile(null);
    setError("");

    try {
      const [commentData, attachmentData] = await Promise.all([
        apiRequest(`/tasks/${task.id}/comments/`),
        apiRequest(`/tasks/${task.id}/attachments/`),
      ]);

      setComments(commentData);
      setAttachments(attachmentData);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddComment(event) {
    event.preventDefault();

    if (!commentText.trim() || !activeTask) return;

    setError("");

    try {
      const comment = await apiRequest(
        `/tasks/${activeTask.id}/comments/`,
        {
          method: "POST",
          body: JSON.stringify({ body: commentText.trim() }),
        }
      );

      setComments((current) => [...current, comment]);
      setCommentText("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleUploadAttachment(event) {
    event.preventDefault();

    if (!selectedFile || !activeTask) return;

    const formData = new FormData();
    formData.append("file", selectedFile);
    setError("");

    try {
      const attachment = await apiRequest(
        `/tasks/${activeTask.id}/attachments/`,
        {
          method: "POST",
          body: formData,
        }
      );

      setAttachments((current) => [...current, attachment]);
      setSelectedFile(null);
      setFileInputKey((current) => current + 1);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username, password, tenantId);
      setPassword("");
      setSignedIn(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleBoardChange(event) {
    const selectedId = event.target.value;
    setBoardId(selectedId);
    setTasks([]);
    setError("");

    try {
      const data = await apiRequest(`/tasks/?board=${selectedId}`);
      setTasks(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleAddTask(status) {
    const title = window.prompt("Task title:");

    if (!title?.trim() || !boardId) return;

    setError("");

    try {
      const task = await apiRequest("/tasks/", {
        method: "POST",
        body: JSON.stringify({
          board: Number(boardId),
          title: title.trim(),
          status,
          priority: "medium",
        }),
      });

      setTasks((current) => [...current, task]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDrop(event, status) {
    event.preventDefault();

    const taskId = event.dataTransfer.getData("text/plain");
    if (!taskId) return;

    setError("");

    try {
      const updatedTask = await apiRequest(`/tasks/${taskId}/`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });

      setTasks((current) =>
        current.map((task) =>
          task.id === updatedTask.id ? updatedTask : task
        )
      );
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleStartCheckout() {
    setError("");
    setBillingLoading(true);

    try {
      const session = await createCheckoutSession();

      if (!session?.url) {
        throw new Error("Stripe did not return a checkout link.");
      }

      window.location.assign(session.url);
    } catch (err) {
      setError(err.message);
      setBillingLoading(false);
    }
  }

  function closeTask() {
    setActiveTask(null);
    setComments([]);
    setAttachments([]);
    setCommentText("");
    setSelectedFile(null);
    setError("");
  }

  function handleLogout() {
    sessionStorage.removeItem("apiToken");
    sessionStorage.removeItem("tenantId");
    setSignedIn(false);
    setBoards([]);
    setTasks([]);
    setBoardId("");
    setBillingStatus(null);
    closeTask();
  }

  if (!signedIn) {
    return (
      <main className="login-page">
        <form className="login-card" onSubmit={handleLogin}>
          <p className="eyebrow">PROJECT WORKSPACE</p>
          <h1>Sign in</h1>
          <p className="muted">Use your Django account and workspace ID.</p>

          <label>
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          <label>
            Tenant ID
            <input
              value={tenantId}
              onChange={(event) => setTenantId(event.target.value)}
              required
            />
          </label>

          {error && <p className="error">{error}</p>}

          <button className="primary" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <div>
          <p className="eyebrow">YOUR WORKSPACE</p>
          <h1>Project board</h1>
        </div>

        <div className="header-actions">
          {boards.length > 0 && (
            <select value={boardId} onChange={handleBoardChange}>
              {boards.map((board) => (
                <option key={board.id} value={board.id}>
                  {board.name}
                </option>
              ))}
            </select>
          )}

          <button
            className="secondary"
            onClick={handleStartCheckout}
            disabled={
              loading ||
              billingLoading ||
              billingStatus?.has_pro_access
            }
          >
            {billingStatus?.has_pro_access
              ? "Pro plan active"
              : billingLoading
                ? "Opening checkout..."
                : "Subscribe to Pro"}
          </button>

          <button className="secondary" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      {error && !activeTask && <p className="error">{error}</p>}
      {loading && <p className="muted">Loading workspace...</p>}

      {!loading && boards.length === 0 && (
        <p className="empty">No boards found for this workspace yet.</p>
      )}

      {boards.length > 0 && (
        <section className="board">
          {columns.map((column) => {
            const columnTasks = tasks.filter(
              (task) => task.status === column.id
            );

            return (
              <div
                className="column"
                key={column.id}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => handleDrop(event, column.id)}
              >
                <div className="column-heading">
                  <h2>{column.label}</h2>
                  <span>{columnTasks.length}</span>
                </div>

                {columnTasks.map((task) => (
                  <article
                    className="task"
                    key={task.id}
                    draggable
                    onDragStart={(event) =>
                      event.dataTransfer.setData(
                        "text/plain",
                        String(task.id)
                      )
                    }
                  >
                    <strong>{task.title}</strong>
                    <p>{task.description || "No description"}</p>
                    <small>
                      {task.priority} priority · #{task.id}
                    </small>

                    <button
                      className="task-details"
                      onClick={() => openTask(task)}
                    >
                      Comments & files
                    </button>
                  </article>
                ))}

                <button
                  className="add-task"
                  onClick={() => handleAddTask(column.id)}
                >
                  + Add task
                </button>
              </div>
            );
          })}
        </section>
      )}

      {activeTask && (
        <div className="modal-backdrop" onClick={closeTask}>
          <section
            className="task-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <button className="modal-close" onClick={closeTask}>
              Close
            </button>

            <p className="eyebrow">TASK #{activeTask.id}</p>
            <h2>{activeTask.title}</h2>

            <h3>Comments</h3>
            {error && <p className="error">{error}</p>}

            <div className="comment-list">
              {comments.length === 0 ? (
                <p className="muted">No comments yet.</p>
              ) : (
                comments.map((comment) => (
                  <article className="comment" key={comment.id}>
                    <strong>{comment.author_name}</strong>
                    <p>{comment.body}</p>
                    <small>
                      {new Date(comment.created_at).toLocaleString()}
                    </small>
                  </article>
                ))
              )}
            </div>

            <form onSubmit={handleAddComment} className="comment-form">
              <textarea
                value={commentText}
                onChange={(event) => setCommentText(event.target.value)}
                placeholder="Write a comment..."
                rows="3"
                required
              />
              <button className="primary">Add comment</button>
            </form>

            <h3>Attachments</h3>

            {attachments.length === 0 ? (
              <p className="muted">No attachments yet.</p>
            ) : (
              <ul className="attachment-list">
                {attachments.map((attachment) => (
                  <li key={attachment.id}>
                    <a
                      href={attachment.file}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {attachment.file.split("/").pop()}
                    </a>{" "}
                    by {attachment.uploaded_by_name}
                  </li>
                ))}
              </ul>
            )}

            <form
              onSubmit={handleUploadAttachment}
              className="attachment-form"
            >
              <input
                key={fileInputKey}
                type="file"
                onChange={(event) =>
                  setSelectedFile(event.target.files?.[0] || null)
                }
                required
              />
              <button className="primary" disabled={!selectedFile}>
                Upload attachment
              </button>
            </form>
          </section>
        </div>
      )}
    </main>
  );
}

export default App;