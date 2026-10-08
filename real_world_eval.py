import argparse
import csv
import json
import os

from engine.risk_analyzer import RiskAnalyzer
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score

VALID_LABELS = {'low', 'medium', 'high'}


def load_examples(path, text_field='text', label_field='label'):
    ext = os.path.splitext(path)[1].lower()
    examples = []

    if ext == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get('examples') or data.get('data') or []
        if not isinstance(data, list):
            raise ValueError('JSON dataset must contain a list of examples.')
        for item in data:
            if not isinstance(item, dict):
                continue
            examples.append({
                'text': item.get(text_field, ''),
                'label': item.get(label_field, ''),
            })
    elif ext == '.csv':
        with open(path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for item in reader:
                examples.append({
                    'text': item.get(text_field, ''),
                    'label': item.get(label_field, ''),
                })
    else:
        raise ValueError('Unsupported file format. Use .csv or .json.')

    return examples


def clean_label(label):
    if label is None:
        return ''
    return str(label).strip().lower()


def validate_examples(examples):
    cleaned = []
    invalid_count = 0
    for item in examples:
        text = item.get('text')
        label = clean_label(item.get('label'))
        if not text or label not in VALID_LABELS:
            invalid_count += 1
            continue
        cleaned.append({'text': text, 'label': label})
    return cleaned, invalid_count


def compute_metrics(true_labels, pred_labels):
    return {
        'accuracy': float(accuracy_score(true_labels, pred_labels)),
        'precision_weighted': float(precision_score(true_labels, pred_labels, average='weighted', zero_division=0)),
        'recall_weighted': float(recall_score(true_labels, pred_labels, average='weighted', zero_division=0)),
        'f1_weighted': float(f1_score(true_labels, pred_labels, average='weighted', zero_division=0)),
        'classification_report': classification_report(true_labels, pred_labels, zero_division=0, digits=4),
    }


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate ClauseGuard risk classification on a labeled dataset.'
    )
    parser.add_argument('path', help='Path to a labeled JSON or CSV dataset')
    parser.add_argument('--text-field', default='text', help='Field name for clause text (default: text)')
    parser.add_argument('--label-field', default='label', help='Field name for true risk labels (default: label)')
    parser.add_argument('--show-sample', type=int, default=0, help='Show the first N predictions')
    args = parser.parse_args()

    examples = load_examples(args.path, text_field=args.text_field, label_field=args.label_field)
    if not examples:
        raise SystemExit('No examples found in the dataset.')

    examples, invalid_count = validate_examples(examples)
    if not examples:
        raise SystemExit('No valid examples with supported labels (low, medium, high).')

    analyzer = RiskAnalyzer()
    true_labels = []
    pred_labels = []
    sample_rows = []

    for item in examples:
        text = item['text']
        true_label = item['label']
        predicted = analyzer.analyze(text)['risk_level']
        true_labels.append(true_label)
        pred_labels.append(predicted)
        if args.show_sample and len(sample_rows) < args.show_sample:
            sample_rows.append({
                'text': text,
                'true_label': true_label,
                'predicted_label': predicted,
            })

    metrics = compute_metrics(true_labels, pred_labels)

    print('Real-world evaluation results')
    print('--------------------------------')
    print(f'Total examples: {len(true_labels)}')
    if invalid_count:
        print(f'Skipped invalid examples: {invalid_count}')
    print(f"Accuracy: {metrics['accuracy']:.4f}")
    print(f"Precision (weighted): {metrics['precision_weighted']:.4f}")
    print(f"Recall (weighted): {metrics['recall_weighted']:.4f}")
    print(f"F1 score (weighted): {metrics['f1_weighted']:.4f}")
    print('\nClassification report:\n')
    print(metrics['classification_report'])

    if sample_rows:
        print('\nSample predictions:')
        for sample in sample_rows:
            print(f"- true={sample['true_label']} predicted={sample['predicted_label']} text={sample['text'][:120]!r}")


if __name__ == '__main__':
    main()
