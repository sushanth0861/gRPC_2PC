# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: twopc.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0btwopc.proto\x12\x05twopc\"+\n\x11InitializeRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\"%\n\x0bVoteRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\"\x1c\n\x0cVoteResponse\x12\x0c\n\x04vote\x18\x01 \x01(\x08\"\'\n\rCommitRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\"!\n\x0e\x43ommitResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\"&\n\x0c\x41\x62ortRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\" \n\rAbortResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\",\n\x12\x46\x65tchCommitRequest\x12\x16\n\x0etransaction_id\x18\x01 \x01(\t\"%\n\x13\x46\x65tchCommitResponse\x12\x0e\n\x06\x63ommit\x18\x01 \x01(\x08\"\x07\n\x05\x45mpty2\xff\x02\n\x05TwoPC\x12\x34\n\nInitialize\x12\x18.twopc.InitializeRequest\x1a\x0c.twopc.Empty\x12\x32\n\x07Prepare\x12\x12.twopc.VoteRequest\x1a\x13.twopc.VoteResponse\x12\x35\n\x06\x43ommit\x12\x14.twopc.CommitRequest\x1a\x15.twopc.CommitResponse\x12\x32\n\x05\x41\x62ort\x12\x13.twopc.AbortRequest\x1a\x14.twopc.AbortResponse\x12\x44\n\x0b\x46\x65tchCommit\x12\x19.twopc.FetchCommitRequest\x1a\x1a.twopc.FetchCommitResponse\x12.\n\x10RestrictDBAccess\x12\x0c.twopc.Empty\x1a\x0c.twopc.Empty\x12+\n\rAllowDBAccess\x12\x0c.twopc.Empty\x1a\x0c.twopc.Emptyb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'twopc_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_INITIALIZEREQUEST']._serialized_start=22
  _globals['_INITIALIZEREQUEST']._serialized_end=65
  _globals['_VOTEREQUEST']._serialized_start=67
  _globals['_VOTEREQUEST']._serialized_end=104
  _globals['_VOTERESPONSE']._serialized_start=106
  _globals['_VOTERESPONSE']._serialized_end=134
  _globals['_COMMITREQUEST']._serialized_start=136
  _globals['_COMMITREQUEST']._serialized_end=175
  _globals['_COMMITRESPONSE']._serialized_start=177
  _globals['_COMMITRESPONSE']._serialized_end=210
  _globals['_ABORTREQUEST']._serialized_start=212
  _globals['_ABORTREQUEST']._serialized_end=250
  _globals['_ABORTRESPONSE']._serialized_start=252
  _globals['_ABORTRESPONSE']._serialized_end=284
  _globals['_FETCHCOMMITREQUEST']._serialized_start=286
  _globals['_FETCHCOMMITREQUEST']._serialized_end=330
  _globals['_FETCHCOMMITRESPONSE']._serialized_start=332
  _globals['_FETCHCOMMITRESPONSE']._serialized_end=369
  _globals['_EMPTY']._serialized_start=371
  _globals['_EMPTY']._serialized_end=378
  _globals['_TWOPC']._serialized_start=381
  _globals['_TWOPC']._serialized_end=764
# @@protoc_insertion_point(module_scope)
