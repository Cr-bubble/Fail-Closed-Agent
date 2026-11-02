# Paper 1 計畫:Fail-Closed Routing Agent(架構 + 實驗 TODO)

目標 venue:ICLAD 2027(預計 ~2027/03 截稿)或 MLCAD 2027(~2027/05);6 頁 IEEE 雙欄雙盲。
工作 branch:`paper/routing-study`。實驗產物放 `paper_exp/<實驗編號>/`。

工作標題候選:
- *Routing, Not Reasoning: A Fail-Closed LLM Agent for Natural-Language Netlist Transformation*
- *The LLM Never Touches the Netlist: Closed-World Intent Routing with Verified Transformation*

一句話定位:LLM 只做「一句話→一個封閉世界 intent」的翻譯,所有電路工作由確定性引擎執行、所有變更過三道 guard;在此架構保證下,用 1,420 句真實請求做控制變因研究,回答「小型凍結模型的 routing 到底被什麼限制」。

---

## 一、論文章節架構

1. **Introduction**(~1 頁)
   - P1 任務與風險結構:Problem A、lock-step 協定、all-or-nothing 計分
   - P2 兩個限制:失敗不對稱(錯誤碰到網表=連坐歸零)、指定凍結小模型;prior work 都讓 LLM 的錯誤有路徑到達成品
   - P3 Thesis:LLM 是翻譯器不是推理器;幻覺損害被結構性封頂在「路由錯誤」
   - P4 量測研究預告:86.9→95.3/97.8、recall與e2e脫鉤、瓶頸=近義intent辨別
   - P5 量測效度:67.2% 假分數事件 + 遙測
   - P6 端到端結果 + Contributions(C1 架構、C2 量測研究、C3 反直覺發現、C4 評測效度)
2. **Background & Related Work**(~0.5 頁)
   - LLM-EDA agent(ChatEDA、Ask-EDA、RTLFixer、VerilogEval/RTLLM)、tool-use(Gorilla/ToolLLM/BFCL)、LLM-Modulo/generate-and-verify
3. **System: Fail-Closed Architecture**(~1.25 頁;Fig.1 系統圖、Fig.2 routing pipeline)
   - 3.1 封閉世界 intent contract(~80 intents、schema、消歧區塊;catalog 永遠全量在 static prompt)
   - 3.2 Routing pipeline:prompt-cached catalog + BM25 top-k=50 相似**例句**(非 tool docs)→ JSON → 語法驗證+一次修正 → 對活網表的 name-grounding → dispatch;design principle: *retrieve demonstrations, not the tool list*(壞檢索永不移除正確答案)
   - 3.3 確定性引擎與 guards:register-cut CEC(對本 DFF model 為 sound sequential 等價)、結構界限重算、basis 純度、snapshot rollback、delta 記帳
   - 3.4 損害上限論證(fail-closed:最壞=路由錯,永不交出壞網表)
4. **Measurement Study**(~2 頁)
   - 4.1 協定:1,420 句、leave-one-testcase-out、N≥5 變異數、兩個指定模型
   - 4.2 Ablation ladder:catalog → +消歧 → +檢索(k 掃描)→ +修正 → 換模型(Fig.3)
   - 4.3 檢索分析:六後端 recall vs e2e 脫鉤、k=100 回歸、examples-vs-docs 天花板(Table 1)
   - 4.4 失敗分類:giveup vs wrong-pick、近義混淆對、hybrid regex 可為淨負(Table 2)
   - 4.5 Baselines:監督式分類器(E1)、native function-calling(E7)、開源小模型(E8)
5. **Measurement Integrity**(~0.5 頁):67.2% 事件、degraded counter + INVALID RUN、第二次實抓、三方獨立驗答、檢索衛生
6. **End-to-End Results**(~0.5 頁):40 公開 case HARD 全過、beta 664.89/680、(11 月名次)、成本/延遲(cache 79%、BM25 0.5ms)
7. **Limitations & Threats to Validity**(~0.25 頁):單一領域、資料釋出、凍結模型時效
8. **Conclusion**

圖表清單:Fig.1 架構圖、Fig.2 routing pipeline、Fig.3 ablation ladder、Table 1 檢索後端、Table 2 失敗分類、Fig.4 fault-injection 損害曲線、Table 3 成本/延遲、Table 4 分類器 baseline 對照。

---

## 二、實驗 TODO

**規則:所有打 API 的實驗一律串行執行(單一 job),不得並行搶 quota——67.2% 事件的教訓。**
每個實驗在 `paper_exp/<ID>/` 下留:執行腳本、原始輸出(per-sentence JSONL)、`SUMMARY.md`(含確切 model id、日期、commit)。

### P0 — 定生死,先跑
- [ ] **E1 監督式分類器 baseline(本地,免 API)**:TF-IDF+LogReg / LinearSVC / BM25-kNN,兩種協定:(a) 只用 public bank 940 句訓練(對齊 LLM 可用資源)、(b) 全部標註資料 leave-one-case-out。**若 intent 準確率 ≥ LLM,整篇要改框架**(改為:分類器選 intent + LLM 填參數?)。注意:分類器只能選 op、不能抽 params——paper 裡要寫明這個範圍差異。
- [ ] **E2 釘死 baseline(API,~$0.15)**:catalog-only、gpt-4o-mini、記錄確切 model、取代「86.9%(模型未記錄)」。
- [ ] **E3 haiku k=50 重跑(API,~$1)**:dedup 後的 97.8% 需重驗;先 --limit 50 煙霧測試再全跑;quota 失敗就記錄 INVALID。

### P1 — 嚴謹度
- [ ] **E4 變異數**:headline 設定各 N≥5(4o-mini k=50、haiku k=50、catalog-only),報 CI;相鄰 ablation 階用 McNemar。
- [ ] **E5 完整 ablation grid**:catalog / +消歧 / +檢索 k∈{0,5,10,25,50,100} / +修正開關 / +name-grounding 開關,同一 bank 版本上重跑。
- [ ] **E6 Fault-injection(本地,ABC)**:污染 p%∈{5,20,50} 的 intent(換錯 intent、壞參數、不安全轉換),量:不安全 commit 攔截率(預期 100%)、答案層損害、rollback 正確性 → C1 的科學證據。
- [ ] **E12 成本/延遲表**:billed tokens、$/1k requests、p50/p95、cache 命中遙測。

### P2 — 防禦力
- [ ] **E7 native function-calling baseline**(OpenAI tools / Anthropic tool_use)vs JSON prompting。
- [ ] **E8 開源小模型**(Qwen2.5-7B / Llama-3.1-8B)。
- [ ] **E9 Transfer domain**(OpenROAD/yosys 指令路由小 bank)——反駁 contest-specific 的關鍵。
- [ ] **E10 標註再裁決**:近義混淆對(reachable_from↔transitive_fanout 等)雙人標註 + κ,dual-report。
- [ ] **E11 受控重現 67.2%**:設計過的 contention 實驗(並行 job / proxy 注入 429),取代當時的偶發事件數字。

### P3 — 加分
- [ ] k=100 回歸重現、union budget-split bug 量化、prompt-cache 4,096 token 門檻跨 provider 重現、binary 大小/可攜性表。

### 行政
- [ ] 向主辦方(Cadence)確認 contest 句子/Q&A 的再散布權利(benchmark 釋出的存亡問題)。
- [ ] ICCAD 2026(11/8–12)名次確定後更新 §6 與 cover letter。

---

## 三、已知數字的內部警告(投稿前必須解決)
1. 86.9% baseline 當時模型未記錄 → E2 取代。
2. 97.8% 是 dedup 前、quota 中斷未重跑 → E3 取代。
3. 多數結果為單次 run → E4 補誤差棒。
4. hybrid<pure 的結論只基於 test91-100 單一 split → E4/E5 內重驗。
