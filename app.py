from flask import Flask, render_template, request, send_file
import pandas as pd
import os

app = Flask(__name__)

# 定義各元素的最低儀器檢測極限
detection_limits = {
    'Ag': 1,
    'Ca': 35,
    'Cd': 2.1,
    'Cr': 2,
    'Cu': 1,
    'Fe': 8,
    'K': 3,
    'Mn': 1,
    'Ni': 2,
    'Pb': 1.1,
    'Rb': 1,
    'Sr': 1,
    'Ti': 4.4,  # 若有 Ti 濃度欄位則使用
    'Zn': 1,
    'Zr': 1.1
}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # 取得使用者上傳的檔案
        file = request.files["file"]
        if not file:
            return "請上傳 CSV 檔案！"

        # 讀取 CSV
        df_all = pd.read_csv(file)

        # 移除重複的欄位（保留第一次出現的）
        df_all = df_all.loc[:, ~df_all.columns.duplicated()]

        # 欲提取的欄位（Sample ID + 元素濃度）
        cols_to_extract = ["Sample ID"] + [f"{element} Concentration" for element in detection_limits.keys()]

        # 確保所有需要的欄位存在
        for col in cols_to_extract:
            if col not in df_all.columns:
                df_all[col] = pd.NA

        # 只提取所需欄位
        df_selected = df_all[cols_to_extract].copy()

        # 重新命名欄位（去掉 "Concentration"）
        renamed_columns = {"Sample ID": "Sample ID"}
        for col in df_selected.columns:
            if col != "Sample ID":
                element = col.split()[0]
                renamed_columns[col] = element
        df_selected = df_selected.rename(columns=renamed_columns)

        # 重新排列欄位：Sample ID 放第一列，其他元素欄位按 ASCII 順序
        sample_id_col = "Sample ID"
        element_cols_sorted = sorted(df_selected.columns.difference([sample_id_col]))
        df_selected = df_selected[[sample_id_col] + element_cols_sorted]

        # 處理數值（<LOD 或低於儀器檢測極限轉為 "ND"）
        def process_value(val, element):
            if pd.isna(val):
                return val
            if isinstance(val, str) and '<LOD' in val:
                return 'ND'
            try:
                num = float(val)
                return 'ND' if num < detection_limits[element] else val
            except Exception:
                return val

        for col in element_cols_sorted:
            df_selected[col] = df_selected[col].apply(lambda x: process_value(x, col))

        # 根據 Sample ID 最後一個英文字母分類
        def get_last_letter(sample_id):
            if isinstance(sample_id, str):
                return sample_id.split('-')[-1] if '-' in sample_id else sample_id[-1]
            return ''

        df_selected['group'] = df_selected[sample_id_col].apply(get_last_letter)

        # 分組輸出
        df_C = df_selected[df_selected['group'] == 'C'].drop(columns='group')
        df_A = df_selected[df_selected['group'] == 'A'].drop(columns='group')

        # 儲存處理後的 CSV
        output_C_path = "output_C.csv"
        output_A_path = "output_A.csv"
        df_C.to_csv(output_C_path, index=False)
        df_A.to_csv(output_A_path, index=False)

        return render_template("index.html", files_ready=True)

    return render_template("index.html", files_ready=False)

@app.route("/download/<filename>")
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
