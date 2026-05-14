import { fireEvent, render, screen } from '@testing-library/react';
import ResearchResults from './ResearchResults';

jest.mock('remark-gfm', () => 'remark-gfm-plugin');
jest.mock('react-markdown', () => ({ children, remarkPlugins = [] }) => {
  if (remarkPlugins.includes('remark-gfm-plugin') && children.includes('|---')) {
    return (
      <table>
        <thead>
          <tr>
            <th>技术路线</th>
            <th>优势</th>
            <th>挑战</th>
            <th>代表性机构</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>超导</td>
            <td>操作速度快、商业化领先</td>
            <td>噪声与误差率高</td>
            <td>IBM、Google</td>
          </tr>
        </tbody>
      </table>
    );
  }
  return <div>{children}</div>;
});

const resultData = {
  query: 'AI 产业趋势',
  timestamp: '2026-05-12T00:00:00+00:00',
  report: '# 报告',
  plan: [
    {
      step: 1,
      title: 'AI 产业采用率有哪些最新数据？',
      dimension: '数据趋势',
      rationale: '需要量化判断市场变化。',
      description: '需要量化判断市场变化。',
      search_queries: [
        'AI adoption rate 2026 enterprise survey',
        'AI 企业采用率 调研 2026',
      ],
      expected_outcome: '获得企业采用率、样本和时间范围。',
      evidence_targets: ['统计数据', '行业报告'],
      depth: 1,
      deep_research_reason: '缺少分行业样本，需要继续深挖。',
      evidence_gaps: ['缺少制造业样本'],
      follow_up_queries: ['AI adoption manufacturing survey 2026'],
      deep_research_stop_condition: '补足分行业样本或达到最大深度',
    },
  ],
  results: [],
};

test('renders structured research plan fields in the process tab', () => {
  render(<ResearchResults data={resultData} />);

  fireEvent.click(screen.getByRole('button', { name: /研究过程/ }));

  expect(screen.getByText('数据趋势')).toBeInTheDocument();
  expect(screen.getByText('需要量化判断市场变化。')).toBeInTheDocument();
  expect(screen.getByText('AI adoption rate 2026 enterprise survey')).toBeInTheDocument();
  expect(screen.getByText('AI 企业采用率 调研 2026')).toBeInTheDocument();
  expect(screen.getByText('获得企业采用率、样本和时间范围。')).toBeInTheDocument();
  expect(screen.getByText('统计数据')).toBeInTheDocument();
  expect(screen.getByText('行业报告')).toBeInTheDocument();
  expect(screen.getByText('深挖记录')).toBeInTheDocument();
  expect(screen.getByText('缺少分行业样本，需要继续深挖。')).toBeInTheDocument();
  expect(screen.getByText('缺少制造业样本')).toBeInTheDocument();
  expect(screen.getByText('AI adoption manufacturing survey 2026')).toBeInTheDocument();
  expect(screen.getByText('补足分行业样本或达到最大深度')).toBeInTheDocument();
});

test('renders markdown pipe tables as actual tables', () => {
  render(
    <ResearchResults
      data={{
        ...resultData,
        report: [
          '## 技术路线对比',
          '',
          '| 技术路线 | 优势 | 挑战 | 代表性机构 |',
          '|---|---|---|---|',
          '| 超导 | 操作速度快、商业化领先 | 噪声与误差率高 | IBM、Google |',
          '| 离子阱 | 门保真度高、连接性好 | 操作速度慢 | IonQ |',
        ].join('\n'),
      }}
    />
  );

  expect(screen.getByRole('table')).toBeInTheDocument();
  expect(screen.getByRole('columnheader', { name: '技术路线' })).toBeInTheDocument();
  expect(screen.getByRole('cell', { name: '超导' })).toBeInTheDocument();
  expect(screen.queryByText(/\|---\|---/)).not.toBeInTheDocument();
});
