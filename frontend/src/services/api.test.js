import { TextDecoder, TextEncoder } from 'util';

jest.mock('axios', () => {
  const post = jest.fn();
  return {
    __mockPost: post,
    create: jest.fn(() => ({
      post,
      get: jest.fn(),
      delete: jest.fn(),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    })),
  };
});

import axios from 'axios';
import { researchAPI } from './api';

global.TextDecoder = TextDecoder;
global.TextEncoder = TextEncoder;

const mockPost = axios.__mockPost;

const streamChunk = (payload) => {
  const encoder = new TextEncoder();
  return encoder.encode(`data: ${JSON.stringify(payload)}\n\n`);
};

test('startResearchStream sends explicit deep research config', async () => {
  const fetchMock = jest.fn().mockResolvedValue({
    ok: true,
    body: {
      getReader: () => {
        let readCount = 0;
        return {
          read: jest.fn().mockImplementation(async () => {
            readCount += 1;
            if (readCount === 1) {
              return {
                done: false,
                value: streamChunk({ type: 'report_complete', data: {} }),
              };
            }
            return { done: true, value: undefined };
          }),
        };
      },
    },
  });
  global.fetch = fetchMock;
  const onUpdate = jest.fn();

  await researchAPI.startResearchStream('AI 产业趋势', onUpdate);

  const requestPayload = JSON.parse(fetchMock.mock.calls[0][1].body);
  expect(requestPayload).toEqual({
    query: 'AI 产业趋势',
    stream: true,
    config: {
      report_type: 'deep',
      deep_research_breadth: 2,
      deep_research_depth: 2,
    },
  });
  expect(onUpdate).toHaveBeenCalledWith({ type: 'report_complete', data: {} });
});

test('startResearch sends explicit deep research config for non-stream fallback', async () => {
  mockPost.mockResolvedValueOnce({ data: { status: 'completed' } });

  await researchAPI.startResearch('AI 产业趋势');

  expect(mockPost).toHaveBeenCalledWith('/api/research', {
    query: 'AI 产业趋势',
    stream: false,
    config: {
      report_type: 'deep',
      deep_research_breadth: 2,
      deep_research_depth: 2,
    },
  });
});

test('previewResearchPlan calls the plan endpoint with deep config', async () => {
  mockPost.mockResolvedValueOnce({ data: { status: 'planned' } });

  await researchAPI.previewResearchPlan('AI 产业趋势');

  expect(mockPost).toHaveBeenCalledWith('/api/research/plan', {
    query: 'AI 产业趋势',
    config: {
      report_type: 'deep',
      deep_research_breadth: 2,
      deep_research_depth: 2,
    },
  });
});

test('startResearchStream sends confirmed plan items when provided', async () => {
  const fetchMock = jest.fn().mockResolvedValue({
    ok: true,
    body: {
      getReader: () => ({
        read: jest.fn().mockResolvedValue({ done: true, value: undefined }),
      }),
    },
  });
  global.fetch = fetchMock;

  await researchAPI.startResearchStream('AI 产业趋势', jest.fn(), {
    planItems: [
      {
        step: 1,
        title: 'AI 产业采用率',
        search_queries: ['AI adoption survey'],
      },
    ],
  });

  const requestPayload = JSON.parse(fetchMock.mock.calls[0][1].body);
  expect(requestPayload.plan_items[0].title).toBe('AI 产业采用率');
});
