import pandas as pd
from jinja2 import Template
import os, json, ast

# Load data
def load_data():
    e_path = 'db/enriched.csv'
    f_path = 'db/final_outreach.csv'
    df_enriched = pd.read_csv(e_path) if os.path.exists(e_path) else pd.DataFrame()
    df_final = pd.read_csv(f_path) if os.path.exists(f_path) else pd.DataFrame()
    return df_enriched, df_final

# Safely parse decision_makers field

def parse_decision_makers(val):
    if isinstance(val, list): return val
    if isinstance(val, str):
        try: return json.loads(val)
        except: pass
        try: return ast.literal_eval(val)
        except: pass
    return []

# HTML template: two columns, left table, right message

template = '''
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Outreach Dashboard</title>
<style>
  body {font-family: Arial, sans-serif; margin:20px;}
  .wrapper {display:flex;}
  .left {width:50%; padding-right:20px;}
  .right {width:50%; padding-left:20px; border-left:1px solid #ddd;}
  table {width:100%; border-collapse:collapse;}
  th, td {border:1px solid #ccc; padding:8px; text-align:left;}
  th {background:#f5f5f5;}
  h2 {margin-top:0;}
  input, textarea, select {width:100%; margin-top:8px; font-size:14px; padding:6px; box-sizing:border-box;}
  textarea {height:200px;}
</style>
</head>
<body>
  <div class="wrapper">
    <div class="left">
      <h2>Actionable Leads</h2>
      <table>
        <thead><tr>
          <th>Company</th><th>Location</th><th>Description</th><th>Contact</th><th>LinkedIn</th>
        </tr></thead>
        <tbody>
        {% for row in leads %}
          <tr>
            <td>{{ row.Company }}</td>
            <td>{{ row.Location }}</td>
            <td>{{ row.Description }}</td>
            <td>{{ row.Contact }}</td>
            <td><a href="{{ row.LinkedIn }}" target="_blank">Profile</a></td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="right">
      <h2>Outreach Message</h2>
      <select id="lead-select">
        {% for row in leads %}
          <option value="{{ loop.index0 }}" {% if loop.first %}selected{% endif %}>{{ row.Company }}</option>
        {% endfor %}
      </select>
      <input type="text" id="subject" value="{{ default_subject }}">
      <textarea id="body">{{ default_body }}</textarea>
    </div>
  </div>
  <script>
    const data = {{ messages|safe }};
    const select = document.getElementById('lead-select');
    const subj = document.getElementById('subject');
    const body = document.getElementById('body');
    select.addEventListener('change', () => {
      const idx = select.value;
      subj.value = data[idx].subject;
      body.value = data[idx].body;
    });
  </script>
</body>
</html>
'''

# Main render
def main():
    df_enriched, df_final = load_data()
    # Filter actionable
    df_act = df_enriched[df_enriched['actionable'].str.lower()=='yes'] if 'actionable' in df_enriched else pd.DataFrame()
    leads = []
    messages = []
    # Determine key for final
    key_col = None
    for c in ['lead_name','company_name','Company']:
        if c in df_final.columns:
            key_col = c; break
    for _, r in df_act.iterrows():
        dms = parse_decision_makers(r.get('decision_makers', []))
        contact = dms[0].get('name','') if dms else ''
        profile = dms[0].get('profile','') if dms else ''
        leads.append({
            'Company': r.get('name',''),
            'Location': r.get('location',''),
            'Description': (r.get('description','') or '')[:40],
            'Contact': contact,
            'LinkedIn': profile
        })
        # find message
        if key_col:
            msgs = df_final[df_final[key_col]==r.get('name','')]
        else:
            msgs = pd.DataFrame()
        if not msgs.empty:
            last = msgs.iloc[-1]
            messages.append({'subject': last.get('revised_subject',''), 'body': last.get('message','')})
        else:
            messages.append({'subject':'','body':''})
    # Render HTML
    html = Template(template).render(
        leads=leads,
        messages=json.dumps(messages),
        default_subject=messages[0]['subject'] if messages else '',
        default_body=messages[0]['body'] if messages else ''
    )
    with open('dashboard.html','w') as f:
        f.write(html)
    print('Generated dashboard.html')

if __name__=='__main__':
    main()
