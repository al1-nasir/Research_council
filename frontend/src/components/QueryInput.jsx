import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

export default function QueryInput({ onSend, disabled }) {
  const [text, setText] = useState("");
  const ref = useRef(null);

  /* Auto-resize textarea */
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = "24px";
      ref.current.style.height = ref.current.scrollHeight + "px";
    }
  }, [text]);

  const submit = () => {
    const q = text.trim();
    if (!q || disabled) return;
    onSend(q);
    setText("");
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="input-area">
      <div className="input-wrapper">
        <div className="input-box">
          <textarea
            ref={ref}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask a research question… e.g. What is the role of BRCA1 in ovarian cancer?"
            rows={1}
            disabled={disabled}
          />
        </div>
        <button
          className="send-btn"
          onClick={submit}
          disabled={disabled || !text.trim()}
          title="Send"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
