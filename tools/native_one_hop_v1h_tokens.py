"""Pinned tokenizer worker. Local tokenizer/template files only; no model classes."""
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    from transformers import AutoTokenizer
    job = json.loads(Path(sys.argv[1]).read_bytes())
    result = dict(version='v1h-token-accounting-v1', inference_performed=False,
                  python=sys.version, packages={p: version(p) for p in ['transformers', 'tokenizers', 'jinja2']}, models={})
    for model, spec in job['models'].items():
        folder = Path(spec['path'])
        for name, expected in spec['file_sha256'].items():
            if digest((folder / name).read_bytes()) != expected:
                raise ValueError('Changed tokenizer/template: ' + name)
        tokenizer = AutoTokenizer.from_pretrained(folder, local_files_only=True, trust_remote_code=False)
        if tokenizer.chat_template != (folder / 'chat_template.jinja').read_text():
            raise ValueError('Tokenizer/native template file differs')
        def render(messages):
            args = dict(add_generation_prompt=True, enable_thinking=False)
            prompt = tokenizer.apply_chat_template(messages, tokenize=False, **args)
            tokens = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False, **args)
            return dict(input_tokens=len(tokens), output_reserve=512, total_required=len(tokens)+512,
                        fits=len(tokens)+512 < 16384, prompt=prompt, tokens=tokens,
                        prompt_sha256=digest(prompt.encode()), tokens_sha256=digest(json.dumps(tokens, separators=(',', ':')).encode()))
        rows = []
        for item in job['observations']:
            row = {k: item[k] for k in ['condition', 'name', 'case_id', 'kind']}
            for variant in ['original', 'columnar']:
                section = item[variant]
                row[variant] = render(section['messages'])
                if 'prefix_messages' in section:
                    counts = [render(m)['input_tokens'] for m in section['prefix_messages']]
                    row[variant]['section_contributions'] = dict(zip(section['section_names'],
                        [counts[0]] + [b-a for a,b in zip(counts,counts[1:])]))
                    if counts[-1] != row[variant]['input_tokens'] or sum(row[variant]['section_contributions'].values()) != counts[-1]:
                        raise ValueError('Non-additive section accounting')
            rows.append(row)
        parities = []
        for record in spec['historical_parities']:
            actual = render(record['messages'])
            if actual['prompt'] != record['prompt'] or actual['tokens'] != record['tokens']:
                raise ValueError('Retained native template/token parity differs: ' + record['identity'])
            parities.append(record['identity'])
        result['models'][model] = dict(rows=rows, native_parities_reproduced=parities,
                                      tokenizer_files=spec['file_sha256'])
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')


if __name__ == '__main__':
    main()
