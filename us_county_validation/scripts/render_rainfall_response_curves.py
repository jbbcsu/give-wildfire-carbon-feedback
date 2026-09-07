"""Render aggregate-only scientific SVG/PNG figures without new dependencies."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import subprocess


def text(x,y,value,size=14,color='#27364a',anchor='start'):
    return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{html.escape(str(value))}</text>'


def render(data,threshold,ymin,ymax):
    title='Stage mean temperature controls' if threshold is None else f'Daily heat controls: {threshold}°C threshold'
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="920" viewBox="0 0 1120 920">',
         '<rect width="1120" height="920" fill="white"/>',
         '<g font-family="Arial, Helvetica, sans-serif">',
         text(50,38,'Rainfall and crop yields: historical U.S. county associations',25),
         text(50,67,title+' | 1981–2018 selected, matched irrigation-practice sample',16)]
    colors={'quantity':'#126a9c','quantity_timing':'#bd5818'}
    for i,(form,label) in enumerate([('quantity','Rainfall quantity'),('quantity_timing','Quantity + timing controls')]):
        x=50+i*290
        svg.extend([f'<line x1="{x}" x2="{x+32}" y1="94" y2="94" stroke="{colors[form]}" stroke-width="3"/>',text(x+42,99,label,14)])
    for row,crop in enumerate(('corn_grain','soybeans')):
        for col,practice in enumerate(('non_irrigated','irrigated')):
            entries=[r for r in data['curves'] if r['heat_threshold_c']==threshold and r['crop']==crop and r['practice']==practice]
            if len(entries)!=2:
                raise ValueError('incomplete figure panel')
            byform={r['form']:r for r in entries}
            first=byform['quantity'];points=first['points']
            xmin,xmax=points[0]['rainfall_mm'],points[-1]['rainfall_mm']
            x0,y0,width,height=90+col*540,182+row*334,440,208
            X=lambda value:x0+width*(value-xmin)/(xmax-xmin)
            Y=lambda value:y0+height-height*(value-ymin)/(ymax-ymin)
            label=('Corn' if crop=='corn_grain' else 'Soybean')+' — '+('Non-irrigated' if practice=='non_irrigated' else 'Irrigated')
            svg.extend([text(x0,y0-35,label,20),text(x0,y0-13,f'{first["sample"]["counties"]} counties; {first["sample"]["rows"]:,} county-years',13)])
            step=max(5,math.ceil((ymax-ymin)/6/5)*5)
            for tick in range(math.ceil(ymin/step)*step,math.floor(ymax/step)*step+1,step):
                svg.extend([f'<line x1="{x0}" x2="{x0+width}" y1="{Y(tick):.2f}" y2="{Y(tick):.2f}" stroke="#e2e7ed"/>',text(x0-10,Y(tick)+4,f'{tick}%',12,anchor='end')])
            for tick in range(math.ceil(xmin/100)*100,math.floor(xmax/100)*100+1,100):
                svg.append(text(X(tick),y0+height+20,tick,12,anchor='middle'))
            svg.append(f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" fill="none" stroke="#9aa8b5"/>')
            for form in ('quantity','quantity_timing'):
                values=byform[form]['points']
                lower=[(X(p['rainfall_mm']),Y(p['pointwise_ci95_percent'][0])) for p in values]
                upper=[(X(p['rainfall_mm']),Y(p['pointwise_ci95_percent'][1])) for p in values[::-1]]
                polygon=' '.join(f'{x:.2f},{y:.2f}' for x,y in lower+upper)
                line=' '.join(f'{X(p["rainfall_mm"]):.2f},{Y(p["fitted_percent_difference"]):.2f}' for p in values)
                svg.extend([f'<polygon points="{polygon}" fill="{colors[form]}" opacity="0.14"/>',
                            f'<polyline points="{line}" fill="none" stroke="{colors[form]}" stroke-width="2.4"/>'])
            median=X(first['reference_rainfall_mm'])
            svg.extend([f'<line x1="{median:.2f}" x2="{median:.2f}" y1="{y0}" y2="{y0+height}" stroke="#596574" stroke-dasharray="4 4"/>',
                        f'<line x1="{x0}" x2="{x0+width}" y1="{Y(0):.2f}" y2="{Y(0):.2f}" stroke="#596574" stroke-dasharray="4 4"/>',
                        text(x0+width/2,y0+height+43,'Growing-season rainfall (mm)',14,anchor='middle')])
            dry=next(p for p in first['percentile_contrasts'] if p['rainfall_percentile']==.1)
            wet=next(p for p in first['percentile_contrasts'] if p['rainfall_percentile']==.9)
            svg.append(text(x0,y0+height+64,f'County ranges span median and P10: {dry["marginal_range_support"]["fraction_counties"]:.0%}; P90: {wet["marginal_range_support"]["fraction_counties"]:.0%}',12))
    svg.extend([text(50,808,'Vertical scale: fitted yield difference relative to median rainfall (%)',15),
                text(50,836,'Lines hold other regressors fixed; shading shows conditional pointwise 95% intervals.',14),
                text(50,859,'Shown over pooled rainfall percentiles 5–95. County-range support is marginal, not joint weather support.',13),
                text(50,882,'Not nationally representative, causal irrigation effects, climate-change damages, or SCC estimates.',13),'</g></svg>'])
    return '\n'.join(svg)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--outdir',required=True,type=Path)
    parser.add_argument('--node',required=True)
    parser.add_argument('--sharp-module',required=True)
    args=parser.parse_args()
    if args.outdir.exists():
        raise ValueError('figure directory already exists')
    data=json.loads(args.input.read_text())
    if len(data['curves'])!=24 or data['causal_or_scc_result'] is not False:
        raise ValueError('unexpected input identity or claim gate')
    low=min(p['pointwise_ci95_percent'][0] for r in data['curves'] for p in r['points'])
    high=max(p['pointwise_ci95_percent'][1] for r in data['curves'] for p in r['points'])
    ymin=math.floor(min(low,0)/5)*5;ymax=math.ceil(max(high,0)/5)*5
    args.outdir.mkdir(parents=True)
    receipt=dict(input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
                 implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 common_y_limits_percent=[ymin,ymax],figures=[])
    for threshold in (None,29,30):
        stem='baseline' if threshold is None else f'heat_{threshold}c'
        svg=args.outdir/(stem+'.svg');png=args.outdir/(stem+'.png')
        svg.write_text(render(data,threshold,ymin,ymax))
        subprocess.run([args.node,'-e',
            'const sharp=require(process.argv[1]);sharp(process.argv[2]).png().toFile(process.argv[3]).catch(e=>{console.error(e);process.exit(1)});',
            args.sharp_module,str(svg),str(png)],check=True)
        receipt['figures'].append(dict(name=stem,png_sha256=hashlib.sha256(png.read_bytes()).hexdigest()))
    (args.outdir/'render_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Three aggregate-only rainfall-curve SVG/PNG figures rendered')


if __name__=='__main__':
    main()
