/* Revenue Leakage Defender: frontend client. */
document.addEventListener("DOMContentLoaded", () => {
    const $ = (id) => document.getElementById(id);

    const dropzoneInvoice = $("dropzone-invoice");
    const inputInvoice = $("input-invoice");
    const nameInvoice = $("name-invoice");
    const sizeInvoice = $("size-invoice");
    const previewInvoice = $("preview-invoice");

    const dropzoneContract = $("dropzone-contract");
    const inputContract = $("input-contract");
    const nameContract = $("name-contract");
    const sizeContract = $("size-contract");
    const previewContract = $("preview-contract");

    const btnStart = $("btn-start-analysis");
    const btnDemo = $("btn-quick-demo");
    const btnReset = $("btn-reset-analysis");
    const btnCopy = $("btn-copy-email");
    const formError = $("form-error");

    const stepperSection = $("stepper-section");
    const stepperTimer = $("stepper-timer");
    const resultsSection = $("results-section");
    const traceBody = $("trace-body");

    const statusDot = $("status-dot");
    const statusText = $("status-text");
    const llmModeBadge = $("llm-mode-badge");
    const llmModeText = $("llm-mode-text");
    const toastContainer = $("toast-container");

    let invoiceFile = null;
    let contractFile = null;
    let currentReport = null;
    let timerId = null;
    let t0 = 0;

    const MAX_BYTES = 10 * 1024 * 1024;

    checkHealth();
    wireDropzone(dropzoneInvoice, inputInvoice, "invoice");
    wireDropzone(dropzoneContract, inputContract, "contract");

    $("btn-remove-invoice").addEventListener("click", (e) => { e.stopPropagation(); setFile("invoice", null); });
    $("btn-remove-contract").addEventListener("click", (e) => { e.stopPropagation(); setFile("contract", null); });
    btnStart.addEventListener("click", startAnalysis);
    btnReset.addEventListener("click", resetAll);
    btnDemo.addEventListener("click", loadDemo);
    btnCopy.addEventListener("click", copyEmail);
    document.querySelectorAll(".filter-btn").forEach((b) =>
        b.addEventListener("click", () => applyFilter(b))
    );

    // Keyboard access for dropzones
    [dropzoneInvoice, dropzoneContract].forEach((dz) => {
        dz.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); dz.querySelector("input").click(); }
        });
    });

    function fmtBytes(n) {
        if (!n && n !== 0) return "n/d";
        if (n < 1024) return n + " B";
        if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
        return (n / (1024 * 1024)).toFixed(1) + " MB";
    }

    function fmtEUR(n) {
        return "€" + Number(n || 0).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function toast(msg, isError) {
        const el = document.createElement("div");
        el.className = "toast" + (isError ? " error" : "");
        el.textContent = msg;
        toastContainer.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    }

    async function checkHealth() {
        try {
            const res = await fetch("/health");
            if (!res.ok) throw new Error("offline");
            statusDot.classList.remove("offline");
            statusText.textContent = "API online";
            const ds = await fetch("/demo-fixtures/status");
            if (ds.ok) {
                const data = await ds.json();
                llmModeBadge.hidden = false;
                llmModeText.textContent = data.llm_mode === "live_gemini" ? "LLM: Gemini live" : "LLM: mock locale";
            }
        } catch {
            statusDot.classList.add("offline");
            statusText.textContent = "Backend non raggiungibile";
        }
    }

    function validPdf(file) {
        if (!file) return false;
        const okType = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
        if (!okType) { showFormError("Sono accettati solo file PDF."); return false; }
        if (file.size > MAX_BYTES) { showFormError("File troppo grande (limite 10 MB)."); return false; }
        hideFormError();
        return true;
    }

    function showFormError(msg) {
        formError.textContent = msg;
        formError.hidden = false;
    }
    function hideFormError() {
        formError.textContent = "";
        formError.hidden = true;
    }

    function setFile(kind, file) {
        if (kind === "invoice") {
            invoiceFile = file;
            renderFileMeta(previewInvoice, nameInvoice, sizeInvoice, dropzoneInvoice, inputInvoice, file);
        } else {
            contractFile = file;
            renderFileMeta(previewContract, nameContract, sizeContract, dropzoneContract, inputContract, file);
        }
        btnStart.disabled = !(invoiceFile && contractFile);
    }

    function renderFileMeta(preview, nameEl, sizeEl, dz, input, file) {
        if (file) {
            nameEl.textContent = file.name;
            sizeEl.textContent = fmtBytes(file.size);
            preview.hidden = false;
            dz.classList.add("has-file");
        } else {
            preview.hidden = true;
            dz.classList.remove("has-file");
            input.value = "";
        }
    }

    function wireDropzone(dz, input, kind) {
        dz.addEventListener("click", (e) => {
            if (e.target.closest(".link-btn")) return;
            input.click();
        });
        input.addEventListener("change", () => {
            const f = input.files[0];
            if (f && validPdf(f)) setFile(kind, f);
            else input.value = "";
        });
        ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => {
            e.preventDefault(); dz.classList.add("dragover");
        }));
        ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => {
            e.preventDefault(); dz.classList.remove("dragover");
        }));
        dz.addEventListener("drop", (e) => {
            const f = e.dataTransfer.files && e.dataTransfer.files[0];
            if (f && validPdf(f)) setFile(kind, f);
        });
    }

    async function loadDemo() {
        btnDemo.disabled = true;
        const label = btnDemo.textContent;
        btnDemo.textContent = "Caricamento…";
        try {
            const [ir, cr] = await Promise.all([
                fetch("/demo-fixtures/invoice"),
                fetch("/demo-fixtures/contract"),
            ]);
            if (!ir.ok || !cr.ok) throw new Error("download fixture non riuscito");
            const [ib, cb] = await Promise.all([ir.blob(), cr.blob()]);
            setFile("invoice", new File([ib], "fattura_test.pdf", { type: "application/pdf" }));
            setFile("contract", new File([cb], "contratto_test.pdf", { type: "application/pdf" }));
            startAnalysis();
        } catch (err) {
            toast("Errore nel caricamento dei dati di esempio.", true);
        } finally {
            btnDemo.disabled = false;
            btnDemo.textContent = label;
        }
    }

    function stepEls() {
        return [1, 2, 3, 4, 5].map((i) => $("step-item-" + i));
    }

    function logLine(time, node, msg, ok) {
        const div = document.createElement("div");
        div.className = "log-line" + (ok ? " ok" : "");
        const t = document.createElement("span");
        t.className = "log-time";
        t.textContent = "[" + time + "]";
        div.appendChild(t);
        if (node) {
            const n = document.createElement("span");
            n.className = "log-node";
            n.textContent = node;
            div.appendChild(n);
        }
        const m = document.createElement("span");
        m.className = "log-msg";
        m.textContent = msg;
        div.appendChild(m);
        traceBody.appendChild(div);
        traceBody.scrollTop = traceBody.scrollHeight;
    }

    function nodeToStep(node) {
        const steps = stepEls();
        const done = (i) => { steps[i].classList.remove("active"); steps[i].classList.add("completed"); };
        const active = (i) => steps[i].classList.add("active");
        if (node === "parse_documents") { done(0); active(1); }
        else if (node === "extract_contract" || node === "extract_invoice") { done(1); active(2); }
        else if (node === "deterministic_match") { done(2); active(3); }
        else if (node === "llm_contract_reasoning") { done(3); active(4); }
        else if (node === "generate_dispute_report") { done(4); }
    }

    async function startAnalysis() {
        if (!invoiceFile || !contractFile) {
            showFormError("Seleziona entrambi i documenti prima di avviare l'analisi.");
            return;
        }
        hideFormError();
        btnStart.disabled = true;
        btnDemo.disabled = true;
        resultsSection.hidden = true;
        stepperSection.hidden = false;
        stepperSection.scrollIntoView({ block: "nearest" });

        stepEls().forEach((s, i) => {
            s.classList.remove("completed", "active");
            if (i === 0) s.classList.add("active");
        });
        traceBody.textContent = "";
        logLine("0,00 s", "", "Avvio analisi…");

        t0 = performance.now();
        stepperTimer.textContent = "0,0 s";
        clearInterval(timerId);
        timerId = setInterval(() => {
            stepperTimer.textContent = ((performance.now() - t0) / 1000).toLocaleString("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " s";
        }, 100);

        const fd = new FormData();
        fd.append("invoice", invoiceFile);
        fd.append("contract", contractFile);

        try {
            const res = await fetch("/analyze/stream", { method: "POST", body: fd });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || ("HTTP " + res.status));
            }
            const reader = res.body.getReader();
            const dec = new TextDecoder();
            let buf = "";
            let report = null;

            for (;;) {
                const { done, value } = await reader.read();
                if (done) break;
                buf += dec.decode(value, { stream: true });
                const parts = buf.split("\n\n");
                buf = parts.pop();
                for (const part of parts) {
                    const line = part.trim();
                    if (!line.startsWith("data:")) continue;
                    let evt;
                    try { evt = JSON.parse(line.replace(/^data:\s*/, "")); }
                    catch { continue; }
                    if (evt.type === "init") logLine("0,05 s", "", evt.message);
                    else if (evt.type === "node_update") {
                        logLine(String(evt.elapsed).replace(".", ",") + " s", evt.node, evt.summary);
                        nodeToStep(evt.node);
                    } else if (evt.type === "complete") {
                        report = evt.report;
                        logLine(String(evt.elapsed).replace(".", ",") + " s", "fine", "Analisi completata.", true);
                    } else if (evt.type === "error") throw new Error(evt.message);
                }
            }

            clearInterval(timerId);
            const secs = (performance.now() - t0) / 1000;
            stepperTimer.textContent = secs.toLocaleString("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + " s";
            if (!report) throw new Error("Report non ricevuto.");
            currentReport = report;
            stepEls().forEach((s) => { s.classList.remove("active"); s.classList.add("completed"); });

            setTimeout(() => {
                stepperSection.hidden = true;
                renderResults(report, secs);
                btnStart.disabled = false;
                btnDemo.disabled = false;
            }, 400);
        } catch (err) {
            clearInterval(timerId);
            stepperSection.hidden = true;
            btnStart.disabled = false;
            btnDemo.disabled = false;
            toast("Errore durante l'analisi: " + err.message, true);
        }
    }

    function renderResults(report, secs) {
        resultsSection.hidden = false;
        const approved = report.status === "APPROVED";
        const banner = $("result-banner");
        banner.classList.toggle("is-ok", approved);
        banner.classList.toggle("is-bad", !approved);
        $("banner-title").textContent = approved ? "Conforme al contratto" : "Discrepanze rilevate";
        $("banner-desc").textContent = report.analysis_summary || "";
        const tag = $("status-tag");
        tag.textContent = approved ? "Approved" : "Discrepancies found";

        const over = $("kpi-overbilling");
        over.textContent = fmtEUR(report.total_overbilling);
        over.classList.toggle("negative", (report.total_overbilling || 0) > 0);
        over.classList.toggle("zero", !(report.total_overbilling > 0));

        $("kpi-invoice-id").textContent = report.invoice_id || "n/d";
        $("kpi-contract-id").textContent = report.contract_id || "n/d";
        $("kpi-count").textContent = String((report.discrepancies || []).length);
        $("kpi-time").textContent = "Durata " + secs.toFixed(1).replace(".", ",") + " s";

        renderTable(report.discrepancies || []);

        const emailSection = $("email-section");
        if (report.dispute_email_draft) {
            emailSection.hidden = false;
            const parts = String(report.dispute_email_draft).split("\n\n");
            $("email-subject").textContent = parts[0].replace(/^Oggetto:\s*/i, "");
            $("email-body").textContent = parts.slice(1).join("\n\n") || report.dispute_email_draft;
        } else {
            emailSection.hidden = true;
        }
        resultsSection.scrollIntoView({ block: "start" });
    }

    const SEV_IT = { high: "Alta", medium: "Media", low: "Bassa" };

    function renderTable(rows) {
        const tb = $("discrepancies-tbody");
        tb.textContent = "";
        const counts = { all: rows.length, high: 0, medium: 0, low: 0 };
        rows.forEach((d) => {
            const s = String(d.severity || "low").toLowerCase();
            if (counts[s] !== undefined) counts[s]++;
        });
        $("count-all").textContent = counts.all;
        $("count-high").textContent = counts.high;
        $("count-medium").textContent = counts.medium;
        $("count-low").textContent = counts.low;
        $("discrepancies-empty").hidden = rows.length > 0;

        rows.forEach((d, i) => {
            const sev = String(d.severity || "low").toLowerCase();
            const tr = document.createElement("tr");
            tr.dataset.severity = sev;

            const cells = [
                String(i + 1),
                d.field_name || "n/d",
                d.invoice_value || "n/d",
                d.expected_value || "n/d",
                (d.delta != null ? fmtEUR(d.delta) : "n/d"),
                SEV_IT[sev] || sev,
                d.reasoning || "",
            ];
            cells.forEach((val, ci) => {
                const td = document.createElement("td");
                if (ci === 4) td.className = "num";
                if (ci === 5) td.className = "sev sev-" + sev;
                if (ci === 6) td.className = "reason";
                td.textContent = val;
                tr.appendChild(td);
            });
            tb.appendChild(tr);
        });
        applyFilter(document.querySelector(".filter-btn.active") || document.querySelector('[data-filter="all"]'));
    }

    function applyFilter(btn) {
        if (!btn) return;
        document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const f = btn.dataset.filter;
        document.querySelectorAll("#discrepancies-tbody tr").forEach((tr) => {
            tr.style.display = (f === "all" || tr.dataset.severity === f) ? "" : "none";
        });
    }

    async function copyEmail() {
        if (!currentReport || !currentReport.dispute_email_draft) return;
        try {
            await navigator.clipboard.writeText(currentReport.dispute_email_draft);
            btnCopy.textContent = "Copiato";
            setTimeout(() => { btnCopy.textContent = "Copia testo"; }, 2000);
        } catch {
            toast("Copia non riuscita dal browser.", true);
        }
    }

    function resetAll() {
        resultsSection.hidden = true;
        setFile("invoice", null);
        setFile("contract", null);
        window.scrollTo({ top: 0 });
    }
});
