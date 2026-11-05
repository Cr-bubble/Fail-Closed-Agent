# Paper 1 段落級細綱(中文工作版,2026-11-05)

> 用途:與 advisor 討論論文架構的工作文件。英文稿未動工;所有數字標注來源與狀態。
> 數字策略(已決策):**主線用 gpt-4o-mini**(全部可重跑);haiku 97.8% 為歷史量測、
> 額度問題未解前**不重驗**,投稿前必須補跑或降級處理(見 §討論問題 Q3)。

工作標題候選:
- *Routing, Not Reasoning: A Fail-Closed LLM Agent for Natural-Language Netlist Transformation*
- *The LLM Never Touches the Netlist: Closed-World Intent Routing with Verified Transformation*

四條貢獻(寫進 §1 末尾):
- **C1(架構)** fail-closed agent:LLM 限縮為一句→一 intent 的翻譯;所有變更過三道 guard+rollback。131 testcase 零硬性違規;fault-injection 24/24 零不安全 commit(修正 rename 漏洞後 exact)。
- **C2(量測研究)** 1,420 句、leave-one-case-out、完整 ablation:88.5%→95.3%(gpt-4o-mini)。
- **C3(反直覺發現)** recall↔e2e 脫鉤;瓶頸=近義 intent 辨別;stdlib BM25 ≈ dense;hybrid regex 可為淨負;監督式分類器最高 73.3%,取代不了 LLM。
- **C4(評測效度)** silent API degradation 製造假分數(67.2% vs 97.8%)+ 輕量遙測對策。

---

## §1 Introduction(預算 1.0 頁,7 段)

| 段 | 內容 | 用到的數字/素材 |
|---|---|---|
| P1 | NL→EDA 介面興起;Problem A 任務形式化:逐行 NL、持續設計狀態、分析/轉換/最佳化、lock-step 協定 | 題目規格 |
| P2 | 風險結構:all-or-nothing(一個硬性違規=整題 0 分);指定凍結 mini 模型、不能 fine-tune | 計分規則 |
| P3 | 既有 LLM-EDA agent 的共同結構:LLM 產 artifact(script/RTL)→事後檢查,錯誤有路徑到達成品。段尾問句:all-or-nothing 下 agent 該長怎樣? | ChatEDA/RTLFixer 引用 |
| P4 | Thesis:倒置架構——LLM 是翻譯器不是推理器;封閉世界 contract(~80 intents)表達不出不安全操作;三道 guard+rollback;損害封頂於「路由錯誤」 | — |
| P5 | 架構保證正確性後的科學問題:routing 被什麼限制?預告四個發現(C3) | 88.5→95.3;82.1% recall 撐 95%+ e2e;73.3% 分類器 |
| P6 | 量測效度一段:同設定 67.2% vs 97.8% 假分數事件;遙測抓到第二次 | E11 素材 |
| P7 | 端到端結果一句(40 公開全過、beta 664.89/680、名次)+ C1–C4 清單 | §6 數字 |

## §2 Background & Related Work(預算 0.4 頁)

- 任務設定細節(輸入輸出格式、評分)盡量壓進 §1 P1–P2 與 §4.1,§2 純文獻。
- 三群文獻、每群 2–3 句對照:
  1. **LLM-EDA agents**:ChatEDA(fine-tuned planner,LLM 產 tool-call script)、Ask-EDA/ORAssistant(RAG 文件 QA)、RTLFixer(LLM 迭代改 RTL)、VerilogEval/RTLLM(codegen benchmark)→ 共同點:LLM 輸出可達成品。
  2. **Tool-use / function calling**:Gorilla、ToolLLM、BFCL → 檢索「tool docs」且無活狀態 grounding;我們量到 doc-retrieval 的 recall 天花板(65–75%)低於無檢索 baseline。
  3. **LLM-Modulo / generate-and-verify**(Kambhampati 等)→ 我們是其在 all-or-nothing 域的完整系統落地與量化。

## §3 System: Fail-Closed Architecture(預算 1.25 頁;Fig.1、Fig.2)

- **3.1 封閉世界 intent contract**:~80 intents、必選/可選參數 schema、消歧區塊;catalog 全量常駐 static prompt(10,280 tokens,prompt-cached,成本 −79%)。重點句:*檢索永遠是 additive——正確答案永遠在模型可及範圍內*。
- **3.2 Routing pipeline**(Fig.2,五階段):① LLM 翻譯(static catalog + BM25 top-50 相似**例句**,非 tool docs)② 語法驗證(`validate_intent_object`)+ 一次帶錯誤回饋的重選 ③ 語意 name-grounding:name 型參數對照**當下活網表**,撞空→帶回饋 retranslate ④ dispatch 到確定性 handler ⑤ per-run cache 壓 temperature 噪音。Design principle:*retrieve demonstrations, not the tool list*。
- **3.3 Guards 與 commit 紀律**:register-cut CEC 的 soundness 論證(DFF 的 D/CK/RN/SN 全數投影為 pseudo-PO,組合 cec 即 sound 的時序等價);結構界限重算;basis 純度;任一失敗→snapshot rollback。轉換 delta 記帳支援後續計數題。
- **3.4 損害上限論證**:最壞情況=路由錯誤(答錯一題),永不交出功能被改壞的設計;fail-closed 預設(全部失敗→安全 no-op ack)。
- 設計細節留給實驗節的:rename 漏洞與修正(§4.6)、validator crash 修正(§5)。

## §4 Measurement Study(預算 2.0 頁;Fig.3、Table 1–4)

- **4.1 協定**:eval bank 1,420 句(test101-171,71 intents)、retrieval bank 為獨立的 public bank(940 列,531 unique);leave-one-testcase-out;指標 = intent acc(主)、params acc、object acc;N≥5 重跑報 CI(E4,gpt-4o-mini,待跑)。
- **4.2 Ablation ladder**(Fig.3):catalog-only **88.5%**(E2,2026-11-03 釘死)→ +BM25 k=25 → k=50 **95.3%**(歷史值,E4 重驗中)→(haiku 97.8%:歷史值,標註 pending;見 Q3)。逐級增量 + McNemar。
- **4.3 檢索分析**(Table 1):**必須標 bank 來源**——歷史六後端數字(93.9/96.4/98.7@25/50)是舊 bank(examples.jsonl LOTO);新 production-bank BM25:recall@5/10/25/50/100 = 60.2/66.5/76.3/82.1/85.6,14.4% never@100、3 個 intent 結構性不可達(60 句)。核心論證:**82% recall 撐出 95%+ e2e → 脫鉤**;k=100 recall 更高但 e2e 降(94.9<95.3,歷史值);73–99% 失敗案例正確 op 已在 context。BM25 延遲 0.5ms(新量,吻合舊值)。
- **4.4 失敗分析**(Table 2):giveup 107→3、wrong-pick 79→28(歷史);E2 新數字:163 失敗=50 giveup+113 wrong-op,top 混淆 pi_to_po_depth→global_max_depth(11)、check_floating→check_dangling(10);hybrid regex-first 91.5% < 純 LLM 92.4%(單 split,歷史,待重驗)。
- **4.5 監督式分類器 baseline**(Table 3,E1 已完成):資源對齊協定最高 47.4%(BM25 top-1);全資料 LOCO 最高 **73.3%**(TF-IDF+LinearSVC)vs LLM 95.3+;混淆對同家族、錯誤率 ~10×;3 intents 在 bank 中零樣本(分類器不可達、LLM 靠 catalog 可達)。附註:分類器只選 op、不能抽 params——比較已對 LLM 不利。
- **4.6 Fault-injection**(Table 4,E6 pilot 已完成):6 案例×4 污染模式、24 注入;走 guard 路徑 21/21 零不安全 commit;**3 escape 同根因**(rename 未走 guard,改名撞既有 net→雙驅動非等價)→ 一行修正後重驗 **24/24,claim 轉為 exact**;誠實呈現 **drift 7 例**(guards 執行被污染的合約而非原句→答案層損害,回應仍稱成功)——分類 caught/drift/escaped 是方法論貢獻。附帶發現:evaluator 兩個盲點(cec NA 當通過、round-trip 不擋雙驅動)。

## §5 Measurement Integrity(預算 0.4 頁)

- 67.2% 事件:rate-limit 把 LLM 呼叫靜默降級成 no-op ack,458 筆假 giveup,同設定真值 97.8%;對策 = degraded counter + INVALID RUN 判定;第二次真實攔截。
- 補充一句 E2 的教訓:validator 本身被 LLM 畸形輸出炸掉也會汙染整輪量測(unhashable enum 參數→TypeError),已修為回驗證錯誤字串。
- 方法論配套:LOCO 檢索衛生、三方獨立驗答(646 PASS/0 FAIL/34 SKIP)、API 實驗串行紀律。

## §6 End-to-End Results(預算 0.4 頁)

- 40 公開 testcase HARD 全過(ABC 驗證等價);beta **664.89/680**(失分全來自語意歧義,零功能違規);contest 名次(ICCAD 2026,11/8–12 頒獎後填)。
- 部署成本:prompt cache −79% token 成本;BM25 0.5ms/query、零依賴(45MB binary);1,420 句全評 2.5 分鐘、約 $0.25(gpt-4o-mini)。

## §7 Limitations & Threats to Validity(0.25 頁)

單一領域(contest 語彙)、haiku 數字未重驗(若屆時仍未補)、資料釋出待主辦方授權、凍結模型的時效性、E6 的 drift 類損害未被架構擋住(誠實邊界)。

## §8 Conclusion(0.15 頁)

---

## 頁數預算與取捨

1.0+0.4+1.25+2.0+0.4+0.4+0.25+0.15 ≈ **5.85 頁**,不含圖表擠壓——**很緊**。
砍法備選:(a) §5 壓成 §4.7 小節(−0.15);(b) §2 壓到 0.3 頁;(c) Table 2 與 Table 3 合併;(d) Fig.1/Fig.2 合成一張雙 panel。

## 圖表清單

| 編號 | 內容 | 狀態 |
|---|---|---|
| Fig.1 | 系統架構(LLM 封閉世界+確定性引擎+guards) | 待畫 |
| Fig.2 | Routing pipeline 五階段(可與 Fig.1 合併) | 待畫 |
| Fig.3 | Ablation ladder(88.5→95.3,haiku 虛線) | E4 後定稿 |
| Table 1 | 檢索:後端×recall@k×e2e×延遲(標 bank 來源) | ER 完成,e2e 行待 E5 |
| Table 2 | 失敗分類+混淆對 | E2 完成,E4 補 CI |
| Table 3 | 分類器 baseline 對照 | E1 完成 |
| Table 4 | Fault-injection caught/drift/escaped(修正前後) | E6 pilot 完成,全量版待跑 |
| Table 5 | 成本/延遲(可併入正文或 §6) | 部分完成 |

## 與 advisor 的討論問題(建議附答案傾向)

1. **主軸**:系統 paper(C1 為骨)還是量測 paper(C2/C3 為骨)?→ 建議混合:C1 當骨架、C2/C3 當肉,venue 選 ICLAD/MLCAD 都吃這種寫法。
2. **Venue 與時程**:ICLAD(~2027/03,主題最對口)vs MLCAD(~2027/05,多兩個月補實驗)。ICCAD 名次下週出爐,要不要等名次決定敘事強度?
3. **haiku 97.8% 的處理**:(a) 保留但標 historical/pending re-validation;(b) 補驗前完全拿掉,主線只講 gpt-4o-mini;(c) 降為腳註。→ 建議 (a),但投稿前必須補驗,否則轉 (b)。
4. **E6 drift 的呈現**:主文誠實呈現(建議)還是收進 limitations?drift 顯示 guard 的語意邊界,是真發現不是弱點。
5. **Benchmark 釋出**:要不要把 1,420 句資料集列為貢獻?取決於 Cadence 授權(行政 todo)。不行就寫 "available upon organizer permission" 或拿掉。
6. **頁數取捨**:上面砍法 (a)–(d) 選哪些?
