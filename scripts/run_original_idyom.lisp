;;; Run original Common Lisp IDyOM from environment variables.
;;;
;;; Required environment variables:
;;;   IDYOM_DB          sqlite database path
;;;   IDYOM_OUTPUT_DIR  directory for the .dat output
;;;   IDYOM_DATASET_ID  integer dataset id
;;;
;;; Optional:
;;;   IDYOM_MODELS      ltm, ltm+, both+, or stm; default both+
;;;   IDYOM_K           cross-validation folds; default 5
;;;   IDYOM_ORDER_BOUND integer max order, or empty/NIL for unbounded
;;;   IDYOM_DETAIL      output detail level; default 3
;;;   IDYOM_TARGET_VIEWPOINTS Lisp list, default (cpitch)
;;;   IDYOM_SOURCE_VIEWPOINTS Lisp list, default (cpitch)
;;;   IDYOM_ASDF_DIR     local directory containing idyom.asd; default D:/music/external/idyom/
;;;   IDYOM_ROOT         writable IDyOM cache/root directory; default D:/music/output/idyom_work/
;;;   IDYOM_OVERWRITE   t/nil; default t
;;;   IDYOM_EXTRA_LOAD   optional Lisp file to load after :idyom, e.g. custom viewpoints

(defun getenv-required (name)
  (let ((value (sb-ext:posix-getenv name)))
    (unless (and value (> (length value) 0))
      (error "Missing environment variable ~A" name))
    value))

(defun getenv-default (name default)
  (let ((value (sb-ext:posix-getenv name)))
    (if (and value (> (length value) 0)) value default)))

(defun parse-model-symbol (value)
  (let ((lower (string-downcase value)))
    (cond
      ((string= lower "ltm") :ltm)
      ((string= lower "ltm+") :ltm+)
      ((string= lower "both") :both)
      ((string= lower "both+") :both+)
      ((string= lower "stm") :stm)
      ((string= lower "stm-only") :stm)
      (t (error "Unsupported IDYOM_MODELS value: ~A" value)))))

(defun parse-order-bound (value)
  (let ((lower (string-downcase value)))
    (if (or (string= lower "") (string= lower "nil") (string= lower "none") (string= lower "unbounded"))
        nil
        (parse-integer value))))

(defun bool-env (name default)
  (let ((value (sb-ext:posix-getenv name)))
    (if value
        (member (string-downcase value) '("1" "t" "true" "yes" "y") :test #'string=)
        default)))

(defun parse-viewpoints (value)
  (read-from-string value))

(defparameter common-lisp-user::*idyom-root*
  (ensure-directories-exist (getenv-default "IDYOM_ROOT" "D:/music/output/idyom_work/")))

(ql:quickload :clsql-sqlite3)
(let ((asdf-dir (getenv-default "IDYOM_ASDF_DIR" "D:/music/external/idyom/")))
  (pushnew (truename asdf-dir) asdf:*central-registry* :test #'equal))
(ql:quickload :idyom)

(let ((extra-load (getenv-default "IDYOM_EXTRA_LOAD" "")))
  (when (> (length extra-load) 0)
    (format t "~&Loading extra Lisp file: ~A~%" extra-load)
    (load extra-load)))

(let* ((db-path (getenv-required "IDYOM_DB"))
       (output-dir (getenv-required "IDYOM_OUTPUT_DIR"))
       (dataset-id (parse-integer (getenv-required "IDYOM_DATASET_ID")))
       (models (parse-model-symbol (getenv-default "IDYOM_MODELS" "both+")))
       (k (parse-integer (getenv-default "IDYOM_K" "5")))
       (order-bound (parse-order-bound (getenv-default "IDYOM_ORDER_BOUND" "nil")))
       (detail (parse-integer (getenv-default "IDYOM_DETAIL" "3")))
       (target-viewpoints (parse-viewpoints (getenv-default "IDYOM_TARGET_VIEWPOINTS" "(cpitch)")))
       (source-viewpoints (parse-viewpoints (getenv-default "IDYOM_SOURCE_VIEWPOINTS" "(cpitch)")))
       (overwrite (bool-env "IDYOM_OVERWRITE" t))
       (ltmo `(:order-bound ,order-bound))
       (stmo `(:order-bound ,order-bound)))
  (format t "~&IDyOM database: ~A~%" db-path)
  (format t "~&Dataset: ~A | models: ~A | k: ~A | order-bound: ~A | detail: ~A~%" dataset-id models k order-bound detail)
  (format t "~&Target viewpoints: ~A | Source viewpoints: ~A~%" target-viewpoints source-viewpoints)
  (clsql:connect (list db-path) :database-type :sqlite3 :if-exists :old :make-default t)
  (idyom:idyom dataset-id
               target-viewpoints
               source-viewpoints
               :models models
               :k k
               :ltmo ltmo
               :stmo stmo
               :texture :melody
               :detail detail
               :output-path output-dir
               :separator ","
               :null-token "NA"
               :information-measure '(:ic :entropy)
               :overwrite overwrite)
  (clsql:disconnect))
