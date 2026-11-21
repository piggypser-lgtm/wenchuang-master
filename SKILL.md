---
name: wenchuang-master
license: MIT
metadata:
  version: "1.4.0"
description: "\u628a\u7167\u7247\u3001\u63d2\u753b\u3001\u56fe\u6848\u6216\u8bbe\u8ba1\u56fe\u505a\u6210\u53ef 3D \u6253\u5370\u7684\u6587\u521b\uff0c\u5982\u94a5\u5319\u6263\u3001\u624b\u673a\u652f\u67b6\u6216\u4e92\u52a8\u73a9\u5177\u3002\u4e5f\u53ef\u63a5\u7eed\u5df2\u6709\u8bbe\u8ba1\u3001\u6a21\u578b\u6216\u6253\u5370\u5de5\u7a0b\u3002"
---

# Wenchuang Master

## Confirm the image subject

For a new image, this section is all you need. Inspect the supplied image and reply in the user's language. Identify the subject and whether you would use the whole subject or a detail. Describe the visible features worth keeping and what is unclear. Label the proposal v1 (or the current revision). Ask for the image if missing, a choice if several subjects are plausible, or another angle if an obstruction matters.

Offer two choices: accept the subject and move to feasibility, or adjust the subject/features. Wait for an actual reply, even when the product is already specified. If the user asks for a change, revise this proposal and ask again.

## After the user confirms

Read the four criteria once, if missing: run `python -B scripts/read_feasibility.py` from this skill's directory. The ASCII JSON string is the section text; use it directly. Present appearance, function, assembly and print feasibility for the agreed scope. Offer to continue or revise, then wait. A subject confirmation covers only the subject.

## Continue an existing project

Resume at the last accepted deliverable. For the current stage, run `python -B scripts/read_stage.py N` from this skill's directory. The numbers follow the [Chinese workflow](WORKFLOW.md):

1. Subject and feasibility
2. Co-design and dimensions
3. Main view, other views and dimension drawings
4. Modeling, fit samples and refinement
5. Split approved color regions and export
6. Plate layout, slicing and file delivery
7. Send to print and review the physical result

Read only the relevant stage and the linked subsection needed for the current decision. If Python is unavailable, use a UTF-8-capable reader for that section. Reuse complete text already in context. For details of confirmation or project handoff, use `rules` in place of `N`.

Show each independently reviewable result with its revision and outstanding checks. Ask the user to accept or request changes. Wait for explicit acceptance before the next deliverable. Installation, uploads, paid generation and sending a print each require authorization.
