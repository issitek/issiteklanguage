import type { components } from "./openapi";

type Schemas = components["schemas"];

export type User = Schemas["UserOut"];
export type UserUpdate = Schemas["UserUpdate"];
export type Token = Schemas["TokenOut"];
export type RegisterInput = Schemas["RegisterIn"];
export type LoginInput = Schemas["LoginIn"];

export type LessonSummary = Schemas["LessonSummary"];
export type Course = Schemas["CourseOut"];
export type Exercise = Schemas["ExerciseOut"];
export type Lesson = Schemas["LessonOut"];

export type AttemptInput = Schemas["AttemptIn"];
export type AttemptResult = Schemas["AttemptOut"];
export type ProgressItem = Schemas["ProgressItem"];
export type Progress = Schemas["ProgressOut"];
export type LessonComplete = Schemas["LessonCompleteOut"];

export type Consent = Schemas["ConsentOut"];
export type ConsentInput = Schemas["ConsentIn"];

export type Presign = Schemas["PresignOut"];
export type PresignInput = Schemas["PresignIn"];
export type Recording = Schemas["RecordingOut"];
export type TtsReference = Schemas["TtsOut"];
