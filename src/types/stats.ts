/**
 * Type definitions for BenchBoard statistics reporting system
 * Based on OpenAPI schema for sensor data processing performance metrics
 */

export interface StatsReport {
  /** 总运行时间（秒） */
  totalElapsed: number;
  /** 发送请求数 */
  totalSent: number;
  /** 完成请求数 */
  totalOps: number;
  /** 总错误数 */
  totalErrors: number;
  /** 总因为发现落盘时间超时而产生的错误数 */
  totalSaveDelayErrors: number;
  /** 待处理请求数 */
  pending: number;
  /** 各类操作统计 */
  operations: OperationsStats;
  /** 高优先级请求统计（Priority≥3） */
  highPriorityStats: HighPriorityStats;
  /** 性能指标 */
  performanceMetrics: PerformanceMetrics;
  /** 延迟分析 */
  latencyAnalysis: LatencyAnalysis;
}

export interface OperationsStats {
  /** 传感器数据操作统计 */
  sensorData: OperationStat;
  /** 传感器读写操作统计 */
  sensorRW: OperationStat;
  /** 批量操作统计 */
  batchRW: OperationStat;
  /** 查询操作统计 */
  query: OperationStat;
}

export interface OperationStat {
  /** 操作数量 */
  operations: number;
  /** 错误数量 */
  errors: number;
}

export interface HighPriorityStats {
  /** 传感器数据上报高优先级请求数 */
  sensorDataCount: number;
  /** 传感器读写操作高优先级请求数 */
  sensorRWCount: number;
  /** 批量操作高优先级请求数 */
  batchRWCount: number;
  /** 查询操作高优先级请求数 */
  queryCount: number;
  /** 高优先级请求总数 */
  totalCount: number;
  /** 高优先级请求占比（%） */
  percentage: number;
}

export interface PerformanceMetrics {
  /** 平均发送 QPS */
  avgSentQPS: number;
  /** 平均完成 QPS */
  avgCompletedQPS: number;
  /** 错误率（%） */
  errorRate: number;
}

export interface LatencyAnalysis {
  /** 传感器数据延迟分布 */
  sensorData: LatencyDistribution;
  /** 传感器读写延迟分布 */
  sensorRW: LatencyDistribution;
  /** 批量操作延迟分布 */
  batchRW: LatencyDistribution;
  /** 查询操作延迟分布 */
  query: LatencyDistribution;
}

export interface LatencyDistribution {
  /** 平均延迟（ms） */
  avg: number;
  /** 最小延迟（ms） */
  min: number;
  /** 最大延迟（ms） */
  max: number;
  /** 延迟分布桶计数，对应 [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]ms 及 >5000ms */
  buckets: number[];
  /** 高优先级请求数量 */
  highPriorityCount?: number;
  /** 高优先级平均延迟（ms） */
  highPriorityAvg?: number | undefined;
  /** 高优先级最小延迟（ms） */
  highPriorityMin?: number | undefined;
  /** 高优先级最大延迟（ms） */
  highPriorityMax?: number | undefined;
  /** 高优先级延迟分布桶计数，对应 [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]ms 及 >5000ms */
  highPriorityBuckets?: number[];
}

/** 延迟分布桶的边界值（毫秒） */
export const LATENCY_BUCKETS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000];

/** 操作类型枚举 */
export enum OperationType {
  SENSOR_DATA = 'sensorData',
  SENSOR_RW = 'sensorRW',
  BATCH_RW = 'batchRW',
  QUERY = 'query'
}

/** 请求优先级枚举 */
export enum Priority {
  LOW = 1,
  NORMAL = 2,
  HIGH = 3,
  URGENT = 4,
  CRITICAL = 5
} 